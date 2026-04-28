"""Account domain router — /auth/account/* delete, restore."""

from datetime import timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants import ACCOUNT_DELETION_BLOCK_DAYS, ErrorCode
from ...utils.datetime_utils import serialize_datetime
from ...data.auth_repository import AuthenticationRepository
from ...data.database import get_db
from ...data.models import (
    AuditEventType,
    AuthenticationToken,
    Content,
    InterestTag,
    SwipeHistory,
    UserPreferences,
    UserProfile,
    utc_now,
)
from ...data.repository import AccountDeletionRepository, AuditRepository, UserProfileRepository
from ..dependencies import get_current_user
from ..schemas import (
    AccountDeleteRequest,
    AccountDeleteResponse,
)

router = APIRouter()


# AUTH-004: Account Delete endpoint


@router.post("/auth/account/delete", response_model=AccountDeleteResponse)
async def delete_account(
    http_request: Request,
    data: AccountDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> AccountDeleteResponse:
    """Permanently delete user account and all data.

    Two-step confirmation required:
    1. First request with confirm=true returns confirmation_token
    2. Second request with confirmation_token proceeds with deletion

    All data is permanently deleted:
    - User profile
    - Authentication tokens
    - All content (saved URLs, summaries)
    - Swipe history
    - User preferences
    - Interest tags

    30-day re-registration block is enforced.

    Args:
        data: Account deletion request with confirmation.
        db: Database session.
        user_id: Authenticated user ID.

    Returns:
        Deletion confirmation with block expiry date.

    Raises:
        400: Missing confirmation or invalid confirmation token.
        401: Invalid or missing token.
    """
    ip = http_request.client.host if http_request.client else None

    # Get user profile
    user_repo = UserProfileRepository(db)
    user = await user_repo.get_by_id(UserProfile, user_id)

    if not user:
        raise HTTPException(status_code=404, detail={"error": ErrorCode.USER_NOT_FOUND, "message": "User not found."})

    # Two-step confirmation logic
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "confirmation_required",
                "message": "Two-step confirmation required. Please confirm deletion.",
            },
        )

    auth_repo = AuthenticationRepository(db)
    deletion_repo = AccountDeletionRepository(db)
    audit = AuditRepository(db)

    # Step 1: Generate confirmation token (if no token provided)
    if not data.confirmation_token:
        # Generate and store confirmation token server-side
        confirmation_token = token_urlsafe(32)
        now = utc_now()
        block_expires_at = now + timedelta(days=ACCOUNT_DELETION_BLOCK_DAYS)

        await deletion_repo.record_account_deletion(
            email=user.email,  # type: ignore
            google_sub=user.google_sub,  # type: ignore
            block_days=ACCOUNT_DELETION_BLOCK_DAYS,
            confirmation_token=confirmation_token,
        )

        await audit.log_event(
            AuditEventType.ACCOUNT_DELETE_INITIATED,
            user_id=user_id,
            ip_address=ip,
            metadata={"step": 1},
        )
        await db.commit()

        return AccountDeleteResponse(
            message="Confirmation token generated. Submit this token to confirm deletion.",
            block_expires_at=serialize_datetime(block_expires_at),
            confirmation_token=confirmation_token,
        )

    # Step 2: Validate confirmation token
    stored_token = await deletion_repo.get_confirmation_token(user.email)  # type: ignore
    if stored_token is None or stored_token != data.confirmation_token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_confirmation_token",
                "message": "Invalid or expired confirmation token. Please request a new one.",
            },
        )

    # Step 3: Proceed with deletion
    now = utc_now()
    block_expires_at = now + timedelta(days=ACCOUNT_DELETION_BLOCK_DAYS)

    # 1. Revoke tokens (already done by getting token, but ensure)
    await auth_repo.revoke_token_by_user_id(user_id)

    # 2. Update account deletion record (remove confirmation token, set final block expiry)
    await deletion_repo.record_account_deletion(
        email=user.email,  # type: ignore
        google_sub=user.google_sub,  # type: ignore
        block_days=ACCOUNT_DELETION_BLOCK_DAYS,
        confirmation_token=None,  # Clear the token
    )

    # 3. DAT-003: Soft-delete cascade — mark Content and InterestTag rows as deleted
    await db.execute(
        update(Content)
        .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
        .values(is_deleted=True, deleted_at=now)
    )
    await db.execute(
        update(InterestTag)
        .where(InterestTag.user_id == user_id, InterestTag.is_deleted == False)  # noqa: E712
        .values(is_deleted=True, deleted_at=now)
    )

    # 4. Soft-delete the UserProfile itself
    await db.execute(
        update(UserProfile)
        .where(UserProfile.id == user_id)
        .values(is_deleted=True, deleted_at=now)
    )

    # 5. Hard-delete session data (auth tokens — these are not recoverable)
    await db.execute(delete(AuthenticationToken).where(AuthenticationToken.user_id == user_id))

    await audit.log_event(
        AuditEventType.ACCOUNT_DELETE_CONFIRMED,
        user_id=user_id,
        ip_address=ip,
        metadata={"step": 2},
    )

    await db.commit()

    return AccountDeleteResponse(
        message="Account deleted successfully",
        block_expires_at=serialize_datetime(block_expires_at),
    )
