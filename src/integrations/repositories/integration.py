"""Repository for integration state management."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import (
    IntegrationSyncConfig,
    IntegrationSyncLog,
    IntegrationTokens,
    Provider,
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
        # Delete any existing tokens for this user/provider
        await self.session.execute(
            delete(IntegrationTokens).where(
                IntegrationTokens.user_id == user_id,
                IntegrationTokens.provider == provider,
            )
        )

        # Insert new tokens with encryption
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

    async def get_tokens(
        self, user_id: int, provider: str
    ) -> Optional[IntegrationTokens]:
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
        # Check if config exists
        result = await self.session.execute(
            select(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == playlist_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.resource_name = playlist_name
            existing.sync_frequency = sync_frequency
            existing.is_active = 1 if is_active else 0
            await self.session.flush()
            return existing
        else:
            # Create new
            config = IntegrationSyncConfig(
                user_id=user_id,
                provider=provider,
                resource_id=playlist_id,
                resource_name=playlist_name,
                sync_frequency=sync_frequency,
                is_active=1 if is_active else 0,
            )
            self.session.add(config)
            await self.session.flush()
            return config

    async def get_sync_configs(
        self, user_id: int, provider: str
    ) -> list[SyncConfig]:
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

    async def delete_sync_config(
        self, user_id: int, provider: str, resource_id: str
    ) -> bool:
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
            select(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            ).with_for_update()
        )

        await self.session.execute(
            update(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == provider,
                IntegrationSyncConfig.resource_id == resource_id,
            ).values(last_sync_at=sync_time)
        )

    async def get_last_sync(
        self, user_id: int, provider: str, resource_id: str
    ) -> Optional[datetime]:
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
        error_message: Optional[str] = None,
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
        now = datetime.now(timezone.utc)

        # Build conditions based on sync frequency
        conditions = []

        # Hourly: last_sync > 1 hour ago or None
        hourly = (
            (IntegrationSyncConfig.sync_frequency == "hourly")
            & (
                (IntegrationSyncConfig.last_sync_at < now - timedelta(hours=1))
                | (IntegrationSyncConfig.last_sync_at == None)
            )
        )
        conditions.append(hourly)

        # Daily: last_sync > 24 hours ago or None
        daily = (
            (IntegrationSyncConfig.sync_frequency == "daily")
            & (
                (IntegrationSyncConfig.last_sync_at < now - timedelta(days=1))
                | (IntegrationSyncConfig.last_sync_at == None)
            )
        )
        conditions.append(daily)

        # Weekly: last_sync > 7 days ago or None
        weekly = (
            (IntegrationSyncConfig.sync_frequency == "weekly")
            & (
                (IntegrationSyncConfig.last_sync_at < now - timedelta(weeks=1))
                | (IntegrationSyncConfig.last_sync_at == None)
            )
        )
        conditions.append(weekly)

        # Get active configs that are due
        result = await self.session.execute(
            select(IntegrationSyncConfig).where(
                (IntegrationSyncConfig.is_active == 1)
                & (hourly | daily | weekly)
            )
        )
        return result.scalars().all()
