"""Repository for email/password auth tables (AUTH-005).

Handles CRUD for user_auth_methods, email_verification_tokens,
and password_reset_tokens.

Commit boundary policy:
  - create_* methods commit internally (callers depend on it for generated IDs).
  - consume_*, mark_email_verified, update_password do NOT commit; callers
    must commit to keep these mutations atomic with surrounding operations.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import AuthProvider
from src.data.models import EmailVerificationToken, PasswordResetToken, UserAuthMethod
from src.utils.datetime_utils import utc_now


class EmailAuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── UserAuthMethod ────────────────────────────────────────────────────

    async def create_auth_method(
        self,
        user_id: int,
        provider: AuthProvider,
        provider_id: str,
        password_hash: str | None = None,
        email_encrypted: str | None = None,
    ) -> UserAuthMethod:
        method = UserAuthMethod(
            user_id=user_id,
            provider=provider,
            provider_id=provider_id,
            password_hash=password_hash,
            email_encrypted=email_encrypted,
            email_verified=False,
        )
        self._db.add(method)
        await self._db.commit()
        await self._db.refresh(method)
        return method

    async def get_auth_method_by_provider(
        self, provider: AuthProvider, provider_id: str
    ) -> UserAuthMethod | None:
        result = await self._db.execute(
            select(UserAuthMethod).where(
                UserAuthMethod.provider == provider,
                UserAuthMethod.provider_id == provider_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_auth_methods_for_user(self, user_id: int) -> list[UserAuthMethod]:
        result = await self._db.execute(
            select(UserAuthMethod).where(UserAuthMethod.user_id == user_id)
        )
        return list(result.scalars().all())

    async def mark_email_verified(self, method_id: int) -> UserAuthMethod:
        """Mark auth method as email-verified. Caller must commit."""
        result = await self._db.execute(
            select(UserAuthMethod).where(UserAuthMethod.id == method_id)
        )
        method = result.scalar_one()
        method.email_verified = True
        method.verified_at = utc_now()
        return method

    async def update_password(self, method_id: int, new_hash: str) -> UserAuthMethod:
        """Update stored password hash. Caller must commit."""
        result = await self._db.execute(
            select(UserAuthMethod).where(UserAuthMethod.id == method_id)
        )
        method = result.scalar_one()
        method.password_hash = new_hash
        return method

    # ── EmailVerificationToken ────────────────────────────────────────────

    async def create_verification_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._db.add(token)
        await self._db.commit()
        await self._db.refresh(token)
        return token

    async def consume_verification_token(self, token_hash: str) -> EmailVerificationToken | None:
        """Mark token used. Does NOT commit — caller commits atomically with mark_email_verified."""
        result = await self._db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > utc_now(),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        token.used_at = utc_now()
        return token

    async def invalidate_verification_tokens_for_user(self, user_id: int) -> int:
        """Mark all active verification tokens for a user as used. Does NOT commit."""
        now = utc_now()
        result = await self._db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > now,
            )
        )
        tokens = list(result.scalars().all())
        for token in tokens:
            token.used_at = now
        return len(tokens)

    # ── PasswordResetToken ────────────────────────────────────────────────

    async def create_reset_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._db.add(token)
        await self._db.commit()
        await self._db.refresh(token)
        return token

    async def consume_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        """Mark token used. Does NOT commit — caller commits atomically with update_password."""
        result = await self._db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > utc_now(),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        token.used_at = utc_now()
        return token
