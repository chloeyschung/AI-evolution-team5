"""Test factories for AUTH-005. Bypass SMTP and token delivery entirely."""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.email_auth import (
    encrypt_email,
    generate_token,
    hash_password,
    hmac_email,
)
from src.auth.tokens import create_access_token, create_refresh_token
from src.constants import AuthProvider
from src.data.email_auth_repository import EmailAuthRepository
from src.data.models import AuthenticationToken, UserAuthMethod, UserProfile
from src.utils.datetime_utils import utc_now
from src.utils.token_hashing import hash_access_token


async def make_user(
    session: AsyncSession,
    email: str = "factory@example.com",
    password: str = "FactoryPass123!",
) -> tuple[UserProfile, str]:
    """Create a fully verified email/password user.

    Returns:
        (UserProfile, access_token) — token is ready for Authorization header.
    """
    user = UserProfile(email=email, created_at=utc_now(), updated_at=utc_now())
    session.add(user)
    await session.flush()

    repo = EmailAuthRepository(session)
    method = await repo.create_auth_method(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id=hmac_email(email),
        password_hash=hash_password(password),
        email_encrypted=encrypt_email(email),
    )
    await repo.mark_email_verified(method.id)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()
    auth_token = AuthenticationToken(
        user_id=user.id,
        access_token=hash_access_token(access_token),
        refresh_token=hash_access_token(refresh_token),
        expires_at=utc_now() + timedelta(hours=1),
    )
    session.add(auth_token)
    await session.commit()
    await session.refresh(user)
    return user, access_token


async def make_unverified_user(
    session: AsyncSession,
    email: str = "unverified@example.com",
    password: str = "FactoryPass123!",
) -> tuple[UserProfile, UserAuthMethod]:
    """Create an unverified email/password user (for testing verification flow)."""
    user = UserProfile(email=email, created_at=utc_now(), updated_at=utc_now())
    session.add(user)
    await session.flush()

    repo = EmailAuthRepository(session)
    method = await repo.create_auth_method(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id=hmac_email(email),
        password_hash=hash_password(password),
        email_encrypted=encrypt_email(email),
    )
    await session.commit()
    await session.refresh(user)
    return user, method


async def make_verification_token(
    session: AsyncSession,
    user_id: int,
) -> str:
    """Create a verification token and return the raw token string."""
    repo = EmailAuthRepository(session)
    raw, token_hash = generate_token()
    await repo.create_verification_token(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(hours=24),
    )
    await session.commit()
    return raw


async def make_reset_token(
    session: AsyncSession,
    user_id: int,
) -> str:
    """Create a password reset token and return the raw token string."""
    repo = EmailAuthRepository(session)
    raw, token_hash = generate_token()
    await repo.create_reset_token(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(hours=1),
    )
    await session.commit()
    return raw
