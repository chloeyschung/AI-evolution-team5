"""Repository for authentication operations."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import AuthenticationToken, UserProfile
from src.auth import tokens as token_utils
from src.utils.datetime_utils import utc_now


class AuthenticationRepository:
    """Repository for authentication token management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tokens(
        self,
        user_id: int,
        access_expires_in: int = 3600,  # 1 hour
        refresh_expires_in: int = 604800,  # 7 days
    ) -> AuthenticationToken:
        """Create new access and refresh tokens for a user.

        Args:
            user_id: The user ID to create tokens for
            access_expires_in: Access token expiry in seconds (default: 1 hour)
            refresh_expires_in: Refresh token expiry in seconds (default: 7 days)

        Returns:
            AuthenticationToken with generated tokens
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

        # Create new token record
        token = AuthenticationToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        return token

    async def get_token_by_user_id(self, user_id: int) -> Optional[AuthenticationToken]:
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
        return result.scalar_one_or_default(None)

    async def get_token_by_access_token(self, access_token: str) -> Optional[AuthenticationToken]:
        """Get authentication token by access token.

        Args:
            access_token: The access token to look up

        Returns:
            AuthenticationToken if found and valid, None otherwise
        """
        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.access_token == access_token)
            .where(AuthenticationToken.revoked_at.is_(None))
        )
        token = result.scalar_one_or_default(None)

        if token:
            # Check if token is expired
            if token.expires_at < utc_now():
                return None

        return token

    async def get_token_by_refresh_token(self, refresh_token: str) -> Optional[AuthenticationToken]:
        """Get authentication token by refresh token.

        Args:
            refresh_token: The refresh token to look up

        Returns:
            AuthenticationToken if found and not revoked, None otherwise
        """
        result = await self.db.execute(
            select(AuthenticationToken)
            .where(AuthenticationToken.refresh_token == refresh_token)
            .where(AuthenticationToken.revoked_at.is_(None))
        )
        return result.scalar_one_or_default(None)

    async def refresh_access_token(
        self,
        refresh_token: str,
        access_expires_in: int = 3600,
    ) -> Optional[AuthenticationToken]:
        """Refresh access token using refresh token.

        Implements token rotation: issues new refresh token on each refresh.

        Args:
            refresh_token: The current refresh token
            access_expires_in: New access token expiry in seconds

        Returns:
            Updated AuthenticationToken with new tokens, None if refresh failed
        """
        # Get existing token by refresh token
        existing_token = await self.get_token_by_refresh_token(refresh_token)
        if not existing_token:
            return None

        # Generate new tokens (token rotation)
        new_access_token = token_utils.create_access_token(existing_token.user_id)
        new_refresh_token = token_utils.create_refresh_token()
        new_expires_at = utc_now() + timedelta(seconds=access_expires_in)

        # Update token record
        existing_token.access_token = new_access_token
        existing_token.refresh_token = new_refresh_token
        existing_token.expires_at = new_expires_at

        await self.db.commit()
        await self.db.refresh(existing_token)

        return existing_token

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
        token = result.scalar_one_or_default(None)

        if token:
            token.revoked_at = utc_now()
            await self.db.commit()
            return True

        return False

    async def _revoke_existing_tokens(self, user_id: int) -> None:
        """Revoke existing tokens for a user (internal helper).

        Args:
            user_id: The user ID to revoke tokens for
        """
        await self.revoke_token_by_user_id(user_id)
