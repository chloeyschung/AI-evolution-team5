"""Repository for integration state management.

TODO #10 (2026-04-14): Removed Optional import - using | None syntax instead.
TODO #12 (2026-04-14): Extracted common patterns using upsert pattern
TODO #13 (2026-04-14): Moved magic numbers to constants.py
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import DAILY_SYNC_THRESHOLD, HOURLY_SYNC_THRESHOLD, WEEKLY_SYNC_THRESHOLD
from src.data.models import (
    IntegrationSyncConfig,
    IntegrationSyncLog,
    IntegrationTokens,
    OAuthState,
)
from src.integrations.youtube.models import SyncConfig, SyncLog


class IntegrationRepository:
    """Repository for managing third-party integration state."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    # OAuth Tokens

    async def save_tokens(
        self,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> IntegrationTokens:
        """Save or update OAuth tokens for a user.

        Args:
            user_id: User ID
            provider: Provider name (e.g., 'youtube')
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: When access token expires

        Returns:
            Saved IntegrationTokens record.
        """
        # Check if record exists
        existing = await self.get_tokens(user_id, provider)

        if existing:
            # Update existing record with encrypted tokens
            from src.utils.token_encryption import encrypt_token

            existing.access_token = encrypt_token(access_token)
            existing.refresh_token = encrypt_token(refresh_token)
            existing.expires_at = expires_at
            existing.updated_at = datetime.now(UTC)
            await self.session.flush()
            return existing
        else:
            # Create new record with encryption
            token_record = IntegrationTokens.with_encrypted_tokens(
                user_id=user_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            self.session.add(token_record)
            await self.session.flush()
            return token_record

    async def get_tokens(self, user_id: int, provider: str) -> IntegrationTokens | None:
        """Get OAuth tokens for a user.

        Args:
            user_id: User ID
            provider: Provider name

        Returns:
            IntegrationTokens record or None.
        """
        result = await self.session.execute(
            select(IntegrationTokens).where(
                IntegrationTokens.user_id == user_id,
                IntegrationTokens.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def delete_tokens(self, user_id: int, provider: str) -> bool:
        """Delete OAuth tokens for a user.

        Args:
            user_id: User ID
            provider: Provider name

        Returns:
            True if tokens were deleted.
        """
        result = await self.session.execute(
            delete(IntegrationTokens).where(
                IntegrationTokens.user_id == user_id,
                IntegrationTokens.provider == provider,
            )
        )
        return result.rowcount > 0

    # Sync Configuration

    async def save_sync_config(
        self,
        user_id: int,
        provider: str,
        playlist_id: str,
        playlist_name: str,
        sync_frequency: str,
        is_active: bool = True,
    ) -> IntegrationSyncConfig:
        """Save or update sync configuration.

        Args:
            user_id: User ID
            provider: Provider name
            playlist_id: Resource ID (e.g., playlist ID)
            playlist_name: Resource name
            sync_frequency: Sync frequency (hourly, daily, weekly)
            is_active: Whether sync is active

        Returns:
            Saved IntegrationSyncConfig record.
        """
        # Check if record exists
        existing = await self.get_sync_config(user_id, provider, playlist_id)

        if existing:
            # Update existing record
            existing.resource_name = playlist_name
            existing.sync_frequency = sync_frequency
            existing.is_active = is_active
            await self.session.flush()
            return existing
        else:
            # Create new record
            config = IntegrationSyncConfig(
                user_id=user_id,
                provider=provider,
                resource_id=playlist_id,
                resource_name=playlist_name,
                sync_frequency=sync_frequency,
                is_active=is_active,
            )
            self.session.add(config)
            await self.session.flush()
            return config

    async def get_sync_config(self, user_id: int, provider: str, resource_id: str) -> IntegrationSyncConfig | None:
        """Get sync configuration by user, provider, and resource.

        Args:
            user_id: User ID
            provider: Provider name
            resource_id: Resource ID

        Returns:
            IntegrationSyncConfig record or None.
        """
        result = await self.session.execute(
            select(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_sync_configs(self, user_id: int, provider: str) -> list[SyncConfig]:
        """Get all sync configs for a user and provider.

        Args:
            user_id: User ID
            provider: Provider name

        Returns:
            List of SyncConfig objects.
        """
        result = await self.session.execute(
            select(IntegrationSyncConfig)
            .where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
            )
            .order_by(IntegrationSyncConfig.resource_name)
        )
        records = result.scalars().all()

        return [
            SyncConfig(
                playlist_id=r.resource_id,
                playlist_name=r.resource_name or "",
                sync_frequency=r.sync_frequency,
                is_active=bool(r.is_active),
            )
            for r in records
        ]

    async def delete_sync_config(self, user_id: int, provider: str, resource_id: str) -> bool:
        """Delete a sync configuration.

        Args:
            user_id: User ID
            provider: Provider name
            resource_id: Resource ID

        Returns:
            True if config was deleted.
        """
        result = await self.session.execute(
            delete(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            )
        )
        return result.rowcount > 0

    # Sync State

    async def update_last_sync(
        self,
        user_id: int,
        provider: str,
        resource_id: str,
        sync_time: datetime,
    ) -> None:
        """Update the last sync timestamp for a resource.

        Args:
            user_id: User ID
            provider: Provider name
            resource_id: Resource ID
            sync_time: When sync completed
        """
        await self.session.execute(
            select(IntegrationSyncConfig)
            .where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            )
            .with_for_update()
        )

        await self.session.execute(
            update(IntegrationSyncConfig)
            .where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            )
            .values(last_sync_at=sync_time)
        )

    async def get_last_sync(self, user_id: int, provider: str, resource_id: str) -> datetime | None:
        """Get the last sync timestamp for a resource.

        Args:
            user_id: User ID
            provider: Provider name
            resource_id: Resource ID

        Returns:
            Last sync timestamp or None.
        """
        result = await self.session.execute(
            select(IntegrationSyncConfig.last_sync_at).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            )
        )
        return result.scalar_one_or_none()

    # Sync Logging

    async def log_sync(
        self,
        user_id: int,
        provider: str,
        resource_id: str,
        status: str,
        ingested_count: int,
        skipped_count: int,
        error_message: str | None = None,
    ) -> IntegrationSyncLog:
        """Log a sync operation.

        Args:
            user_id: User ID
            provider: Provider name
            resource_id: Resource ID
            status: 'success', 'failed', or 'partial'
            ingested_count: Number of items ingested
            skipped_count: Number of items skipped
            error_message: Optional error message

        Returns:
            Created IntegrationSyncLog record.
        """
        log = IntegrationSyncLog(
            user_id=user_id,
            provider=provider,
            resource_id=resource_id,
            status=status,
            ingested_count=ingested_count,
            skipped_count=skipped_count,
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.flush()

        return log

    async def get_sync_logs(
        self,
        user_id: int,
        provider: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SyncLog]:
        """Get sync logs for a user.

        Args:
            user_id: User ID
            provider: Provider name
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of SyncLog objects.
        """
        result = await self.session.execute(
            select(IntegrationSyncLog)
            .where(
                IntegrationSyncLog.user_id == user_id,
                IntegrationSyncLog.provider == provider,
            )
            .order_by(IntegrationSyncLog.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        records = result.scalars().all()

        return [
            SyncLog(
                id=r.id,
                user_id=r.user_id,
                playlist_id=r.resource_id,
                status=r.status,
                ingested_count=r.ingested_count,
                skipped_count=r.skipped_count,
                error_message=r.error_message,
                executed_at=r.executed_at,
            )
            for r in records
        ]

    async def get_due_syncs(self) -> list[IntegrationSyncConfig]:
        """Get sync configs that are due to run.

        Returns:
            List of IntegrationSyncConfig records due for sync.
        """
        now = datetime.now(UTC)

        # Build due conditions using CASE-like logic
        # Each frequency has its own time threshold
        hourly_due = (IntegrationSyncConfig.sync_frequency == "hourly") & (
            (IntegrationSyncConfig.last_sync_at < now - timedelta(hours=HOURLY_SYNC_THRESHOLD))
            | (IntegrationSyncConfig.last_sync_at.is_(None))
        )

        daily_due = (IntegrationSyncConfig.sync_frequency == "daily") & (
            (IntegrationSyncConfig.last_sync_at < now - timedelta(hours=DAILY_SYNC_THRESHOLD))
            | (IntegrationSyncConfig.last_sync_at.is_(None))
        )

        weekly_due = (IntegrationSyncConfig.sync_frequency == "weekly") & (
            (IntegrationSyncConfig.last_sync_at < now - timedelta(hours=WEEKLY_SYNC_THRESHOLD))
            | (IntegrationSyncConfig.last_sync_at.is_(None))
        )

        # Get active configs that are due
        result = await self.session.execute(
            select(IntegrationSyncConfig).where(IntegrationSyncConfig.is_active & (hourly_due | daily_due | weekly_due))
        )
        return result.scalars().all()

    # OAuth CSRF State Tokens (SEC-002)

    async def save_oauth_state(
        self,
        user_id: int,
        provider: str,
        state_token: str,
        expires_at: datetime,
    ) -> OAuthState:
        """Store a single-use OAuth CSRF state token.

        Args:
            user_id: User initiating the OAuth flow.
            provider: Provider name (e.g., 'youtube').
            state_token: Cryptographically random token from secrets.token_urlsafe.
            expires_at: When this token expires (15-minute TTL recommended).

        Returns:
            Created OAuthState record.
        """
        record = OAuthState(
            user_id=user_id,
            provider=provider,
            state_token=state_token,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_and_consume_oauth_state(
        self,
        state_token: str,
        provider: str,
    ) -> int | None:
        """Look up a valid unexpired state token, delete it, and return its user_id.

        Single-use: the row is deleted on first match. Subsequent calls with the
        same token return None (replay protection).

        Args:
            state_token: Token from OAuth callback query param.
            provider: Provider name to scope the lookup.

        Returns:
            user_id if token is valid and unexpired, else None.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(OAuthState).where(
                OAuthState.state_token == state_token,
                OAuthState.provider == provider,
                OAuthState.expires_at > now,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        user_id = record.user_id
        await self.session.execute(
            delete(OAuthState).where(OAuthState.id == record.id)
        )
        return user_id
