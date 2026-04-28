"""Repository for authentication operations.

TODO #10 (2026-04-14): Removed Optional import - using | None syntax instead.
"""

from asyncio import Lock
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import tokens as token_utils
from src.data.base_repository import BaseRepository
from src.data.models import AuthenticationToken
from src.utils.datetime_utils import convert_to_utc, utc_now
from src.utils.token_hashing import hash_access_token


class AuthenticationRepository(BaseRepository[AuthenticationToken]):
    """Repository for authentication token management."""
    REFRESH_TOKEN_TTL_SECONDS = 604800  # 7 days
    _refresh_locks: dict[str, Lock] = {}
    _refresh_locks_guard: Lock = Lock()

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db  # Keep for backward compatibility

    @classmethod
    async def _get_refresh_lock(cls, lock_key: str) -> Lock:
        """Get (or create) a per-refresh-token rotation lock."""
        async with cls._refresh_locks_guard:
            lock = cls._refresh_locks.get(lock_key)
            if lock is None:
                lock = Lock()
                cls._refresh_locks[lock_key] = lock
            return lock

    async def create_tokens(
        self,
        user_id: int,
        access_expires_in: int = 3600,  # 1 hour
        refresh_expires_in: int = 604800,  # 7 days
    ) -> tuple[AuthenticationToken, str]:
        """Create new access and refresh tokens for a user.

        Args:
            user_id: The user ID to create tokens for
            access_expires_in: Access token expiry in seconds (default: 1 hour)
            refresh_expires_in: Refresh token expiry in seconds (default: 7 days)

        Returns:
            Tuple of (AuthenticationToken with hashed access token, plaintext JWT access token)
        """
        # Generate JWT access token
        access_token = token_utils.create_access_token(user_id)

        # Generate opaque refresh token
        refresh_token = token_utils.create_refresh_token()

        # Calculate expiry times
        now = utc_now()
        expires_at = now + timedelta(seconds=access_expires_in)

        # Check if tokens already exist and revoke them (token rotation)
        await self._revoke_existing_tokens(user_id)

        # Create new token record with hashed access and refresh tokens
        token = AuthenticationToken(
            user_id=user_id,
            access_token=hash_access_token(access_token),  # Hash for secure storage
            refresh_token=hash_access_token(refresh_token),  # Hash for secure storage
            expires_at=expires_at,
        )

        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        return token, access_token, refresh_token  # hashed record + plaintext JWT + plaintext refresh token

    async def get_token_by_user_id(self, user_id: int) -> AuthenticationToken | None:
        """Get authentication token by user ID.

        Args:
            user_id: The user ID to look up

        Returns:
            AuthenticationToken if found and not revoked, None otherwise
        """
        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.user_id == user_id)
            .where(AuthenticationToken.revoked_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_token_by_access_token(self, access_token: str) -> AuthenticationToken | None:
        """Get authentication token by access token.

        Args:
            access_token: The access token to look up

        Returns:
            AuthenticationToken if found and valid, None otherwise
        """
        # Hash the access token for comparison
        hashed_token = hash_access_token(access_token)

        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.access_token == hashed_token)
            .where(AuthenticationToken.revoked_at.is_(None))
        )
        token = result.scalar_one_or_none()

        if token:
            # Check if token is expired
            # Convert to UTC to handle timezone-aware/naive comparison
            from src.utils.datetime_utils import convert_to_utc

            expires_at_utc = convert_to_utc(token.expires_at)
            if expires_at_utc and expires_at_utc < utc_now():
                return None

        return token

    async def get_token_by_refresh_token(self, refresh_token: str) -> AuthenticationToken | None:
        """Get authentication token by refresh token.

        Args:
            refresh_token: The refresh token to look up

        Returns:
            AuthenticationToken if found and not revoked, None otherwise
        """
        # Hash the refresh token for comparison
        hashed_refresh_token = hash_access_token(refresh_token)

        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.refresh_token == hashed_refresh_token)
            .where(AuthenticationToken.revoked_at.is_(None))
            .with_for_update()  # prevents concurrent rotation race condition
        )
        return result.scalar_one_or_none()

    async def refresh_access_token(
        self,
        refresh_token: str,
        access_expires_in: int = 3600,
    ) -> tuple[AuthenticationToken, str, str] | None:
        """Refresh access token using refresh token.

        Implements token rotation: issues new refresh token on each refresh.

        Args:
            refresh_token: The current refresh token
            access_expires_in: New access token expiry in seconds

        Returns:
            Tuple of (Updated AuthenticationToken, plaintext JWT access token) or None if refresh failed
        """
        # SQLite ignores FOR UPDATE. Serialize by refresh token hash.
        hashed_refresh_token = hash_access_token(refresh_token)
        refresh_lock = await self._get_refresh_lock(hashed_refresh_token)
        async with refresh_lock:
            result = await self.db.execute(
                select(AuthenticationToken)
                .where(AuthenticationToken.refresh_token == hashed_refresh_token)
                .where(AuthenticationToken.revoked_at.is_(None))
            )
            existing_token = result.scalar_one_or_none()
            if not existing_token:
                return None

            # Enforce refresh token TTL from token creation time.
            created_at_utc = convert_to_utc(existing_token.created_at)
            if created_at_utc is None:
                return None
            if utc_now() >= created_at_utc + timedelta(seconds=self.REFRESH_TOKEN_TTL_SECONDS):
                return None

            # Generate new tokens (token rotation)
            new_access_token = token_utils.create_access_token(existing_token.user_id)
            new_refresh_token = token_utils.create_refresh_token()
            new_expires_at = utc_now() + timedelta(seconds=access_expires_in)

            # Update token record with hashed access and refresh tokens
            existing_token.access_token = hash_access_token(new_access_token)
            existing_token.refresh_token = hash_access_token(new_refresh_token)  # Hash for secure storage
            existing_token.expires_at = new_expires_at

            await self.db.commit()
            await self.db.refresh(existing_token)
            return existing_token, new_access_token, new_refresh_token  # hashed record + plaintext JWT + plaintext refresh token

    async def revoke_token_by_user_id(self, user_id: int) -> bool:
        """Revoke all tokens for a user (logout or account delete).

        Args:
            user_id: The user ID to revoke tokens for

        Returns:
            True if tokens were revoked, False if no tokens found
        """
        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.user_id == user_id)
            .where(AuthenticationToken.revoked_at.is_(None))
        )
        token = result.scalar_one_or_none()

        if token:
            token.revoked_at = utc_now()
            await self.db.commit()
            return True

        return False

    async def _revoke_existing_tokens(self, user_id: int) -> None:
        """Revoke existing tokens for a user (internal helper).

        Physically deletes old tokens to avoid unique constraint violation on user_id.

        Args:
            user_id: The user ID to revoke tokens for
        """
        await self.db.execute(
            delete(AuthenticationToken).where(AuthenticationToken.user_id == user_id)
        )
