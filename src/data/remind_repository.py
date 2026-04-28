"""Repositories for reminder system (ADV-003)."""

from datetime import datetime, timedelta
from datetime import time as time_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.datetime_utils import utc_now

from .base_repository import BaseRepository
from .models import (
    ReminderLog,
    ReminderPreference,
    UserActivityPattern,
)


class ReminderPreferenceRepository(BaseRepository[ReminderPreference]):
    """Repository for ReminderPreference."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def get(self, user_id: int) -> ReminderPreference | None:
        """Get reminder preferences for user."""
        result = await self.session.execute(select(ReminderPreference).where(ReminderPreference.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, **kwargs) -> ReminderPreference:
        """Create reminder preferences for user."""
        preference = ReminderPreference(user_id=user_id, **kwargs)
        self.session.add(preference)
        await self.session.commit()
        return preference

    async def update(self, user_id: int, **kwargs) -> ReminderPreference | None:
        """Update reminder preferences for user."""
        preference = await self.get(user_id)
        if not preference:
            return None

        for key, value in kwargs.items():
            if hasattr(preference, key):
                setattr(preference, key, value)

        await self.session.commit()
        return preference

    async def get_or_create(self, user_id: int) -> ReminderPreference:
        """Get or create reminder preferences for user."""
        preference = await self.get(user_id)
        if not preference:
            # Create with defaults
            preference = await self.create(
                user_id=user_id,
                is_enabled=True,
                preferred_time=datetime.combine(datetime.min, time_type(18, 0)),  # 6 PM default
                frequency="daily",
                quiet_hours_start=datetime.combine(datetime.min, time_type(22, 0)),  # 10 PM
                quiet_hours_end=datetime.combine(datetime.min, time_type(8, 0)),  # 8 AM
                backlog_threshold=10,
            )
        return preference


class ReminderLogRepository(BaseRepository[ReminderLog]):
    """Repository for ReminderLog."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def create(
        self,
        user_id: int,
        reminder_type: str,
        message: str,
        sent_at: datetime | None = None,
    ) -> ReminderLog:
        """Create a new reminder log entry."""
        log = ReminderLog(
            user_id=user_id,
            reminder_type=reminder_type,
            message=message,
            sent_at=sent_at or utc_now(),
        )
        self.session.add(log)
        await self.session.commit()
        return log

    async def mark_action_taken(self, user_id: int, log_id: int, action_at: datetime | None = None) -> bool:
        """Mark that user took action on reminder."""
        result = await self.session.execute(
            select(ReminderLog)
            .where(ReminderLog.id == log_id)
            .where(ReminderLog.user_id == user_id)
            .where(~ReminderLog.action_taken)
        )
        log = result.scalar_one_or_none()
        if not log:
            return False

        log.action_taken = True
        log.action_taken_at = action_at or utc_now()
        await self.session.commit()
        return True

    async def mark_dismissed(self, user_id: int, log_id: int, dismissed_at: datetime | None = None) -> bool:
        """Mark that user dismissed the reminder."""
        result = await self.session.execute(
            select(ReminderLog)
            .where(ReminderLog.id == log_id)
            .where(ReminderLog.user_id == user_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            return False

        log.dismissed_at = dismissed_at or utc_now()
        await self.session.commit()
        return True

    async def get_last_reminder(self, user_id: int, reminder_type: str | None = None) -> ReminderLog | None:
        """Get the last reminder sent to user."""
        query = select(ReminderLog).where(ReminderLog.user_id == user_id).order_by(ReminderLog.sent_at.desc())

        if reminder_type:
            query = query.where(ReminderLog.reminder_type == reminder_type)

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_last_reminder_by_type(self, user_id: int, reminder_type: str) -> ReminderLog | None:
        """Get the last reminder of specific type sent to user."""
        result = await self.session.execute(
            select(ReminderLog)
            .where(ReminderLog.user_id == user_id)
            .where(ReminderLog.reminder_type == reminder_type)
            .order_by(ReminderLog.sent_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_response_rate(self, user_id: int, days: int = 30) -> tuple[int, int]:
        """Get (actioned, total) reminder count for user in last N days."""
        cutoff = utc_now() - timedelta(days=days)

        total_result = await self.session.execute(
            select(ReminderLog).where(ReminderLog.user_id == user_id).where(ReminderLog.sent_at >= cutoff)
        )
        total = len(total_result.scalars().all())

        actioned_result = await self.session.execute(
            select(ReminderLog)
            .where(ReminderLog.user_id == user_id)
            .where(ReminderLog.sent_at >= cutoff)
            .where(ReminderLog.action_taken)
        )
        actioned = len(actioned_result.scalars().all())

        return actioned, total


class UserActivityPatternRepository(BaseRepository[UserActivityPattern]):
    """Repository for UserActivityPattern."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def get(self, user_id: int) -> UserActivityPattern | None:
        """Get activity pattern for user."""
        result = await self.session.execute(select(UserActivityPattern).where(UserActivityPattern.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, **kwargs) -> UserActivityPattern:
        """Create activity pattern for user."""
        pattern = UserActivityPattern(user_id=user_id, **kwargs)
        self.session.add(pattern)
        await self.session.commit()
        return pattern

    async def update(self, user_id: int, **kwargs) -> UserActivityPattern | None:
        """Update activity pattern for user."""
        pattern = await self.get(user_id)
        if not pattern:
            return None

        for key, value in kwargs.items():
            if hasattr(pattern, key):
                setattr(pattern, key, value)

        await self.session.commit()
        return pattern

    async def get_or_create(self, user_id: int) -> UserActivityPattern:
        """Get or create activity pattern for user."""
        pattern = await self.get(user_id)
        if not pattern:
            # Create with defaults
            pattern = await self.create(
                user_id=user_id,
                most_active_hour=18,  # 6 PM default
                most_active_day=0,  # Monday default
                avg_daily_swipes=10.0,
                avg_session_duration=15.0,  # 15 minutes
            )
        return pattern
