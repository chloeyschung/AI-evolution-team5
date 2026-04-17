"""Auth domain router — /auth/* login, register, token refresh, Google OAuth."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants import AuthProvider, ErrorCode
from ...data.auth_repository import AuthenticationRepository
from ...data.database import get_db
from ...data.email_auth_repository import EmailAuthRepository
from ...data.models import AuditEventType, UserAuthMethod, UserProfile, utc_now
from ...data.repository import AuditRepository, UserProfileRepository
from ...auth.email_auth import hash_password, hmac_email, encrypt_email, verify_password, generate_token
from ...services.email_service import EmailService
from ...utils.token_hashing import hash_access_token as _hash_token
from ..dependencies import get_current_user
from ..schemas import (
    AuthStatusResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
    GoogleOAuthCodeRequest,
    LinkAccountRequest,
    LinkAccountResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordResetConfirmResponse,
    PasswordResetConfirmSchema,
    PasswordResetRequestResponse,
    PasswordResetRequestSchema,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserProfileResponse,
    VerifyEmailResponse,
)

router = APIRouter()

_VERIFICATION_EMAIL_SENT_MESSAGE = "If that email is registered and not yet verified, a verification email has been sent."


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _rotate_verification_token(email_repo: EmailAuthRepository, user_id: int) -> str:
    await email_repo.invalidate_verification_tokens_for_user(user_id)
    raw_token, token_hash = generate_token()
    await email_repo.create_verification_token(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(hours=24),
    )
    return raw_token


def _send_verification_email_safely(email: str, raw_token: str) -> None:
    try:
        EmailService().send_verification_email(email, raw_token)
    except Exception:
        pass


# AUTH-001: Authentication endpoints


@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None, alias="Authorization"),
) -> AuthStatusResponse:
    """Check current authentication status.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Auth status with user info if authenticated.
    """
    # No token provided
    if not authorization or not authorization.startswith("Bearer "):
        return AuthStatusResponse(is_authenticated=False)

    # Extract token
    token = authorization[7:]  # Remove "Bearer " prefix
    auth_repo = AuthenticationRepository(db)

    # Get token from database
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        return AuthStatusResponse(is_authenticated=False)

    # Return authenticated status
    user_repo = UserProfileRepository(db)
    user = await user_repo.get_user_by_id(token_record.user_id)
    return AuthStatusResponse(
        is_authenticated=True,
        user_id=token_record.user_id,
        email=user.email if user else None,
        display_name=user.display_name if user else None,
        avatar_url=user.avatar_url if user else None,
        token_expires_at=token_record.expires_at.isoformat(),
    )


@router.post("/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_auth_token(
    http_request: Request,
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    """Refresh access token using refresh token.

    Implements token rotation: issues new refresh token on each refresh.

    Args:
        http_request: Incoming HTTP request (for IP extraction).
        data: Refresh token request.
        db: Database session.

    Returns:
        New access token and expiry time.

    Raises:
        401: Invalid or expired refresh token.
    """
    ip = http_request.client.host if http_request.client else None
    auth_repo = AuthenticationRepository(db)

    # Refresh token (includes token rotation)
    refresh_result = await auth_repo.refresh_access_token(data.refresh_token)

    if not refresh_result:
        raise HTTPException(status_code=401, detail=ErrorCode.INVALID_REFRESH_TOKEN)

    token_record, access_token = refresh_result

    # Log refresh event — token_record already has user_id, commit happens inside refresh_access_token
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.REFRESH_TOKEN,
        user_id=token_record.user_id,
        ip_address=ip,
    )
    await db.commit()

    return TokenRefreshResponse(
        access_token=access_token,  # Plaintext JWT for client
        refresh_token=token_record.refresh_token,  # Rotated refresh token
        expires_at=token_record.expires_at.isoformat(),
    )


# AUTH-002: Google OAuth endpoint


@router.post("/auth/google", status_code=200, response_model=GoogleLoginResponse)
async def google_login(
    http_request: Request,
    data: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> GoogleLoginResponse:
    """Authenticate with Google and get access tokens.

    Handles:
    - New user registration (auto-create account)
    - Existing user login (issue new tokens)
    - 30-day re-registration block enforcement

    Args:
        data: Google login request with ID token and user info.
        db: Database session.

    Returns:
        Access tokens and user info.

    Raises:
        401: Invalid Google ID token.
        403: Account within 30-day re-registration block.
    """
    from src.auth.google_oauth import GoogleTokenVerificationError, verify_google_id_token
    from src.config import settings
    from src.data.repository import AccountDeletionRepository, UserProfileRepository

    # Verify Google ID token with audience validation
    try:
        await verify_google_id_token(data.google_id_token, client_id=settings.GOOGLE_CLIENT_ID)
    except GoogleTokenVerificationError as e:
        raise HTTPException(status_code=401, detail=f"{ErrorCode.INVALID_GOOGLE_TOKEN}: {str(e)}") from e

    # Extract user info from request
    email = data.google_user_info.email
    google_sub = data.google_user_info.id

    # Check for 30-day re-registration block
    deletion_repo = AccountDeletionRepository(db)
    is_blocked, block_expires_at = await deletion_repo.is_account_blocked(email=email, google_sub=google_sub)

    if is_blocked:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_restriction",
                "message": "Account recently deleted. Please wait 30 days before re-registering.",
                "available_at": block_expires_at.isoformat(),
            },
        )

    # Check if user already exists
    user_repo = UserProfileRepository(db)
    existing_user = await user_repo.get_user_by_email(email)

    if not existing_user:
        # Check by google_sub as fallback
        existing_user = await user_repo.get_user_by_google_sub(google_sub)

    auth_repo = AuthenticationRepository(db)
    is_new_user = False

    if existing_user:
        # Existing user: update last login
        await user_repo.update_last_login(existing_user.id)
    else:
        # New user: create account
        existing_user = await user_repo.create_user(
            email=email,
            google_sub=google_sub,
            display_name=data.google_user_info.name,
            avatar_url=data.google_user_info.picture,
        )
        is_new_user = True

    # Upsert user_auth_methods row for Google provider (AUTH-005)
    email_auth_repo = EmailAuthRepository(db)
    existing_method = await email_auth_repo.get_auth_method_by_provider(AuthProvider.GOOGLE, google_sub)
    if not existing_method:
        await email_auth_repo.create_auth_method(
            user_id=existing_user.id,
            provider=AuthProvider.GOOGLE,
            provider_id=google_sub,
            email_verified=True,
        )

    # Create authentication tokens (returns tuple of record and plaintext JWT)
    token_record, access_token = await auth_repo.create_tokens(existing_user.id)

    ip = http_request.client.host if http_request.client else None
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=existing_user.id,
        ip_address=ip,
        metadata={"provider": "google"},
    )
    await db.commit()

    return GoogleLoginResponse(
        access_token=access_token,  # Plaintext JWT for client
        refresh_token=token_record.refresh_token,
        expires_at=token_record.expires_at.isoformat(),
        user=UserProfileResponse(
            id=existing_user.id,
            email=existing_user.email,
            display_name=existing_user.display_name,
            avatar_url=existing_user.avatar_url,
            bio=existing_user.bio,
            created_at=existing_user.created_at.isoformat(),
            updated_at=existing_user.updated_at.isoformat(),
        ),
        is_new_user=is_new_user,
    )


@router.post("/auth/google/code", status_code=200, response_model=GoogleLoginResponse)
async def google_login_with_code(
    http_request: Request,
    data: GoogleOAuthCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> GoogleLoginResponse:
    """Authenticate with Google OAuth code exchange (web flow).

    This endpoint handles the full OAuth code exchange on the backend,
    so the client secret never needs to be exposed to the frontend.

    Handles:
    - OAuth code → token exchange (backend with client_secret)
    - New user registration (auto-create account)
    - Existing user login (issue new tokens)
    - 30-day re-registration block enforcement

    Args:
        data: OAuth code from Google redirect.
        db: Database session.

    Returns:
        Access tokens and user info.

    Raises:
        400: Missing or invalid OAuth code.
        401: Invalid Google token.
        403: Account within 30-day re-registration block.
    """
    from src.auth.google_oauth import (
        GoogleTokenVerificationError,
        exchange_auth_code_for_tokens,
    )
    from src.config import settings
    from src.data.repository import AccountDeletionRepository, UserProfileRepository

    if not data.code:
        raise HTTPException(status_code=400, detail="OAuth code is required")

    # Exchange code for tokens (backend has client_secret)
    try:
        id_token, google_user_info = await exchange_auth_code_for_tokens(
            code=data.code,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
    except GoogleTokenVerificationError as e:
        raise HTTPException(status_code=401, detail=f"{ErrorCode.INVALID_GOOGLE_TOKEN}: {str(e)}") from e

    # Extract user info
    email = google_user_info.get("email")
    google_sub = google_user_info.get("sub") or google_user_info.get("id")

    if not email or not google_sub:
        raise HTTPException(status_code=401, detail="Missing email or user ID from Google")

    # Check for 30-day re-registration block
    deletion_repo = AccountDeletionRepository(db)
    is_blocked, block_expires_at = await deletion_repo.is_account_blocked(
        email=email, google_sub=google_sub
    )

    if is_blocked:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_restriction",
                "message": "Account recently deleted. Please wait 30 days before re-registering.",
                "available_at": block_expires_at.isoformat(),
            },
        )

    # Check if user already exists
    user_repo = UserProfileRepository(db)
    existing_user = await user_repo.get_user_by_email(email)

    if not existing_user:
        # Check by google_sub as fallback
        existing_user = await user_repo.get_user_by_google_sub(google_sub)

    auth_repo = AuthenticationRepository(db)
    is_new_user = False

    if existing_user:
        # Existing user: update last login
        await user_repo.update_last_login(existing_user.id)
    else:
        # New user: create account
        existing_user = await user_repo.create_user(
            email=email,
            google_sub=google_sub,
            display_name=google_user_info.get("name"),
            avatar_url=google_user_info.get("picture"),
        )
        is_new_user = True

    # Upsert user_auth_methods row for Google provider (AUTH-005)
    email_auth_repo = EmailAuthRepository(db)
    existing_method = await email_auth_repo.get_auth_method_by_provider(AuthProvider.GOOGLE, google_sub)
    if not existing_method:
        await email_auth_repo.create_auth_method(
            user_id=existing_user.id,
            provider=AuthProvider.GOOGLE,
            provider_id=google_sub,
            email_verified=True,
        )

    # Create authentication tokens (returns tuple of record and plaintext JWT)
    token_record, access_token = await auth_repo.create_tokens(existing_user.id)

    ip = http_request.client.host if http_request.client else None
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=existing_user.id,
        ip_address=ip,
        metadata={"provider": "google"},
    )
    await db.commit()

    return GoogleLoginResponse(
        access_token=access_token,  # Plaintext JWT for client
        refresh_token=token_record.refresh_token,
        expires_at=token_record.expires_at.isoformat(),
        user=UserProfileResponse(
            id=existing_user.id,
            email=existing_user.email,
            display_name=existing_user.display_name,
            avatar_url=existing_user.avatar_url,
            bio=existing_user.bio,
            created_at=existing_user.created_at.isoformat(),
            updated_at=existing_user.updated_at.isoformat(),
        ),
        is_new_user=is_new_user,
    )


# AUTH-005: Email/Password auth routes ────────────────────────────────────────


@router.post("/auth/register", status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    email_repo = EmailAuthRepository(db)
    normalized_email = _normalize_email(request.email)
    provider_id = hmac_email(normalized_email)

    existing = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)
    if existing:
        if existing.email_verified:
            raise HTTPException(
                status_code=409,
                detail={"error": "email_exists", "providers": [AuthProvider.EMAIL_PASSWORD.value]},
            )

        raw_token = await _rotate_verification_token(email_repo, existing.user_id)
        _send_verification_email_safely(normalized_email, raw_token)
        return RegisterResponse(message="Verification email sent. Please check your inbox.")

    user_repo = UserProfileRepository(db)
    existing_user = await user_repo.get_user_by_email(normalized_email)
    if existing_user:
        auth_methods = await email_repo.get_auth_methods_for_user(existing_user.id)
        raise HTTPException(
            status_code=409,
            detail={"error": "email_exists", "providers": [method.provider.value for method in auth_methods]},
        )

    user = UserProfile(
        email=normalized_email,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(user)
    await db.flush()

    await email_repo.create_auth_method(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id=provider_id,
        password_hash=hash_password(request.password),
        email_encrypted=encrypt_email(normalized_email),
    )

    raw_token = await _rotate_verification_token(email_repo, user.id)

    _send_verification_email_safely(normalized_email, raw_token)

    return RegisterResponse(message="Verification email sent. Please check your inbox.")


@router.get("/auth/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> VerifyEmailResponse:
    email_repo = EmailAuthRepository(db)
    token_hash = _hash_token(token)
    token_rec = await email_repo.consume_verification_token(token_hash)
    if token_rec is None:
        raise HTTPException(status_code=400, detail={"error": "invalid_or_expired_token"})

    result = await db.execute(
        select(UserAuthMethod).where(
            UserAuthMethod.user_id == token_rec.user_id,
            UserAuthMethod.provider == AuthProvider.EMAIL_PASSWORD,
        )
    )
    method = result.scalar_one_or_none()
    if method:
        method.email_verified = True
        method.verified_at = utc_now()
    await db.commit()

    return VerifyEmailResponse(message="Email verified. You can now sign in.")


@router.post("/auth/verify-email/resend", response_model=ResendVerificationResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> ResendVerificationResponse:
    email_repo = EmailAuthRepository(db)
    normalized_email = _normalize_email(request.email)
    provider_id = hmac_email(normalized_email)
    method = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)

    if method and not method.email_verified:
        raw_token = await _rotate_verification_token(email_repo, method.user_id)
        _send_verification_email_safely(normalized_email, raw_token)

    return ResendVerificationResponse(message=_VERIFICATION_EMAIL_SENT_MESSAGE)


@router.post("/auth/login")
async def login_email(
    http_request: Request,
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    ip = http_request.client.host if http_request.client else None
    audit = AuditRepository(db)
    email_repo = EmailAuthRepository(db)
    provider_id = hmac_email(request.email)

    method = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)
    if method is None:
        await audit.log_event(
            AuditEventType.LOGIN_FAILURE,
            ip_address=ip,
            metadata={"reason": "user_not_found", "email": request.email},
        )
        await db.commit()
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials"})

    if not verify_password(request.password, method.password_hash or ""):
        await audit.log_event(
            AuditEventType.LOGIN_FAILURE,
            user_id=method.user_id,
            ip_address=ip,
            metadata={"reason": "invalid_password"},
        )
        await db.commit()
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials"})

    if not method.email_verified:
        raise HTTPException(status_code=403, detail={"error": "email_not_verified"})

    user = await db.get(UserProfile, method.user_id)
    if user is None:
        await audit.log_event(
            AuditEventType.LOGIN_FAILURE,
            ip_address=ip,
            metadata={"reason": "user_not_found"},
        )
        await db.commit()
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials"})

    user_repo = UserProfileRepository(db)
    await user_repo.update_last_login(user.id)
    auth_repo = AuthenticationRepository(db)
    token_record, access_token = await auth_repo.create_tokens(user.id)

    await audit.log_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user.id,
        ip_address=ip,
    )
    # db.commit() will be called by auth_repo.create_tokens or the session context

    return LoginResponse(
        access_token=access_token,
        refresh_token=token_record.refresh_token,
        expires_at=token_record.expires_at.isoformat(),
        user_id=user.id,
        email=user.email,
    )


@router.post("/auth/password-reset/request")
async def password_reset_request(
    request: PasswordResetRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetRequestResponse:
    email_repo = EmailAuthRepository(db)
    provider_id = hmac_email(request.email)
    method = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)

    if method:
        raw_token, token_hash = generate_token()
        await email_repo.create_reset_token(
            user_id=method.user_id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=1),
        )
        try:
            EmailService().send_password_reset_email(request.email, raw_token)
        except Exception:
            pass  # Never reveal whether email exists

    return PasswordResetRequestResponse(message="If that email is registered, a reset link has been sent.")


@router.post("/auth/password-reset/confirm")
async def password_reset_confirm(
    request: PasswordResetConfirmSchema,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetConfirmResponse:
    email_repo = EmailAuthRepository(db)
    token_hash = _hash_token(request.token)
    token_rec = await email_repo.consume_reset_token(token_hash)
    if token_rec is None:
        raise HTTPException(status_code=400, detail={"error": "invalid_or_expired_token"})

    result = await db.execute(
        select(UserAuthMethod).where(
            UserAuthMethod.user_id == token_rec.user_id,
            UserAuthMethod.provider == AuthProvider.EMAIL_PASSWORD,
        )
    )
    method = result.scalar_one_or_none()
    if method is None:
        raise HTTPException(status_code=400, detail={"error": "invalid_or_expired_token"})

    method.password_hash = hash_password(request.new_password)
    await db.commit()
    return PasswordResetConfirmResponse(message="Password updated. You can now sign in.")


@router.post("/auth/link-account")
async def link_account(
    request: LinkAccountRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> LinkAccountResponse:
    """Link an email/password identity to an existing account (re-auth required)."""
    email_repo = EmailAuthRepository(db)
    provider_id = hmac_email(request.email)

    existing_method = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)
    if existing_method and existing_method.user_id != user_id:
        raise HTTPException(status_code=409, detail={"error": "email_taken_by_another_account"})
    if existing_method and existing_method.user_id == user_id:
        raise HTTPException(status_code=409, detail={"error": "already_linked"})

    await email_repo.create_auth_method(
        user_id=user_id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id=provider_id,
        password_hash=hash_password(request.password),
        email_encrypted=encrypt_email(request.email),
    )

    return LinkAccountResponse(message="Email/password identity linked. Verify your email to activate it.")


# AUTH-003: Logout endpoint


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> LogoutResponse:
    """End current session and revoke tokens.

    Local data is retained on the client and will sync on re-login.

    Args:
        db: Database session.
        user_id: Authenticated user ID.

    Returns:
        Logout confirmation.

    Raises:
        401: Invalid or missing token.
    """
    auth_repo = AuthenticationRepository(db)
    await auth_repo.revoke_token_by_user_id(user_id)
    return LogoutResponse(message="Logged out successfully")
