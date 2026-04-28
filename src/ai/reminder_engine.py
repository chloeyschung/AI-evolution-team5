"""Smart reminder engine for nudging content consumption (ADV-003)."""

from dataclasses import dataclass
from datetime import UTC, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants import (
    REMINDER_BACKLOG_THRESHOLD,
    ReminderFrequency,
    ReminderPriority,
    ReminderType,
    STREAK_CHECK_DAYS,
)
from ..data.models import (
    Content,
    ContentStatus,
    ReminderPreference,
    SwipeAction,
    SwipeHistory,
    UserActivityPattern,
    UserStreak,
)
from ..data.remind_repository import (
    ReminderLogRepository,
    ReminderPreferenceRepository,
    UserActivityPatternRepository,
)
from ..data.repository import ContentRepository, SwipeRepository
from ..utils.datetime_utils import is_quiet_hours, utc_now


@dataclass
class ReminderSuggestion:
    """A reminder suggestion for the user."""

    reminder_type: ReminderType
    message: str
    priority: ReminderPriority
    metadata: dict


class ReminderEngine:
    """Generate and manage smart reminders."""

    DEFAULT_STREAK_RISK_DAYS = 1  # Warn if no activity today and streak > 0
    DEFAULT_REENGAGEMENT_DAYS = 7  # Warn if no activity for 7+ days

    def __init__(self, db_session: AsyncSession):
        self._preference_repo = ReminderPreferenceRepository(db_session)
        self._pattern_repo = UserActivityPatternRepository(db_session)
        self._log_repo = ReminderLogRepository(db_session)
        self._content_repo = ContentRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)

    async def get_suggestion(self, user_id: int) -> ReminderSuggestion | None:
        """Get current reminder suggestion for user.

        Returns:
            ReminderSuggestion or None if no reminder needed
        """
        preferences = await self._preference_repo.get(user_id)
        if not preferences or not preferences.is_enabled:
            return None

        if self._is_quiet_hours(preferences):
            return None

        if not await self._can_send_reminder(user_id, preferences):
            return None

        reminder = await self._generate_reminder(user_id, preferences)
        return reminder

    def _is_quiet_hours(self, preferences: ReminderPreference) -> bool:
        """Check if current time is within quiet hours."""
        quiet_start = preferences.quiet_hours_start.time() if preferences.quiet_hours_start else None
        quiet_end = preferences.quiet_hours_end.time() if preferences.quiet_hours_end else None

        if not quiet_start or not quiet_end:
            return False

        return is_quiet_hours(utc_now(), quiet_start, quiet_end)

    async def _can_send_reminder(self, user_id: int, preferences: ReminderPreference) -> bool:
        """Check if we can send a reminder based on frequency limits."""
        if preferences.frequency == ReminderFrequency.NEVER:
            return False

        last_reminder = await self._log_repo.get_last_reminder(user_id)
        if not last_reminder:
            return True  # No previous reminders, can send

        now = utc_now()

        if preferences.frequency == ReminderFrequency.DAILY:
            days_since = (now - last_reminder.sent_at).days
            return days_since >= 1
        elif preferences.frequency == ReminderFrequency.WEEKLY:
            days_since = (now - last_reminder.sent_at).days
            return days_since >= 7
        else:
            return True

    async def _generate_reminder(self, user_id: int, preferences: ReminderPreference) -> ReminderSuggestion | None:
        """Generate appropriate reminder based on user state.

        Priority order: streak > backlog > time_based > reengagement
        """
        streak_reminder = await self._check_streak_reminder(user_id)
        if streak_reminder:
            return streak_reminder

        backlog_reminder = await self._check_backlog_reminder(user_id, preferences)
        if backlog_reminder:
            return backlog_reminder

        time_reminder = await self._check_time_based_reminder(user_id, preferences)
        if time_reminder:
            return time_reminder

        reengagement_reminder = await self._check_reengagement_reminder(user_id)
        if reengagement_reminder:
            return reengagement_reminder

        return None

    async def _check_streak_reminder(self, user_id: int) -> ReminderSuggestion | None:
        """Check if user needs a streak reminder.

        Triggered when user has an active streak but no activity today.
        """
        streak = await self._get_user_streak(user_id)

        if not streak or streak.current_streak < 1:
            return None

        last_activity = streak.last_activity_date
        if not last_activity:
            return None

        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)

        if last_activity.tzinfo:
            last_activity_date = last_activity.astimezone(UTC).date()
        else:
            last_activity_date = last_activity.date()

        today_date = today_start.date()

        if last_activity_date == today_date:
            return None

        unread_count = await self._get_unread_count(user_id)

        if unread_count > 0:
            return ReminderSuggestion(
                reminder_type=ReminderType.STREAK,
                message=f"Don't break your {streak.current_streak}-day streak! You have {unread_count} items waiting.",
                priority=ReminderPriority.HIGH,
                metadata={"streak_days": streak.current_streak, "unread_count": unread_count},
            )

        return None

    async def _check_backlog_reminder(
        self, user_id: int, preferences: ReminderPreference
    ) -> ReminderSuggestion | None:
        """Check if user needs a backlog reminder.

        Triggered when unread content exceeds threshold.
        """
        unread_count = await self._get_unread_count(user_id)
        threshold = preferences.backlog_threshold or REMINDER_BACKLOG_THRESHOLD

        if unread_count >= threshold:
            return ReminderSuggestion(
                reminder_type=ReminderType.BACKLOG,
                message=f"You have {unread_count} unread items in your inbox. Ready to catch up?",
                priority=ReminderPriority.MEDIUM,
                metadata={"unread_count": unread_count, "threshold": threshold},
            )

        return None

    async def _check_time_based_reminder(
        self, user_id: int, preferences: ReminderPreference
    ) -> ReminderSuggestion | None:
        """Check if user needs a time-based reminder.

        Triggered at user's preferred consumption time.
        """
        preferred_time = preferences.preferred_time
        if not preferred_time:
            return None

        now = utc_now()
        preferred_hour = preferred_time.hour
        preferred_minute = preferred_time.minute

        time_diff = abs((now.hour * 60 + now.minute) - (preferred_hour * 60 + preferred_minute))
        if time_diff > 60:
            return None

        new_count = await self._get_new_items_count(user_id, days=1)

        if new_count > 0:
            return ReminderSuggestion(
                reminder_type=ReminderType.TIME_BASED,
                message=f"Time for your daily knowledge boost! {new_count} new items since yesterday.",
                priority=ReminderPriority.LOW,
                metadata={"new_count": new_count},
            )

        return None

    async def _check_reengagement_reminder(self, user_id: int) -> ReminderSuggestion | None:
        """Check if user needs a re-engagement reminder.

        Triggered after user hasn't used the app for N days.
        """
        streak = await self._get_user_streak(user_id)

        if not streak or not streak.last_activity_date:
            return None

        now = utc_now()

        if streak.last_activity_date.tzinfo:
            last_activity = streak.last_activity_date.astimezone(UTC)
        else:
            last_activity = streak.last_activity_date.replace(tzinfo=UTC)

        days_inactive = (now - last_activity).days

        if days_inactive >= self.DEFAULT_REENGAGEMENT_DAYS:
            unread_count = await self._get_unread_count(user_id)

            if unread_count > 0:
                return ReminderSuggestion(
                    reminder_type=ReminderType.REENGAGEMENT,
                    message=f"We miss you! {unread_count} items are waiting for you in Briefly.",
                    priority=ReminderPriority.LOW,
                    metadata={"days_inactive": days_inactive, "unread_count": unread_count},
                )

        return None

    async def _get_user_streak(self, user_id: int) -> UserStreak | None:
        """Get user's current streak."""
        result = await self._log_repo.session.execute(
            select(UserStreak).where(UserStreak.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_unread_count(self, user_id: int) -> int:
        """Get count of unread (inbox) items for user."""
        result = await self._log_repo.session.execute(
            select(Content).where(Content.user_id == user_id, Content.status == ContentStatus.INBOX)
        )
        contents = result.scalars().all()
        return len(contents)

    async def _get_new_items_count(self, user_id: int, days: int) -> int:
        """Get count of items kept by user in last N days."""
        cutoff = utc_now() - timedelta(days=days)

        # Get swipe history in last N days with KEEP action
        result = await self._log_repo.session.execute(
            select(SwipeHistory)
            .where(SwipeHistory.user_id == user_id)
            .where(SwipeHistory.action == SwipeAction.KEEP)
            .where(SwipeHistory.swiped_at >= cutoff)
        )
        swipes = result.scalars().all()
        return len(swipes)

    async def log_reminder_sent(self, user_id: int, suggestion: ReminderSuggestion) -> int:
        """Log that a reminder was sent.

        Returns:
            Reminder log ID
        """
        log = await self._log_repo.create(
            user_id=user_id,
            reminder_type=suggestion.reminder_type.value,
            message=suggestion.message,
        )
        return log.id

    async def log_action_taken(self, user_id: int, log_id: int) -> bool:
        """Log that user took action on a reminder."""
        return await self._log_repo.mark_action_taken(user_id, log_id)

    async def log_dismissed(self, user_id: int, log_id: int) -> bool:
        """Log that user dismissed a reminder."""
        return await self._log_repo.mark_dismissed(user_id, log_id)


class ActivityPatternLearner:
    """Learn user activity patterns from swipe history."""

    def __init__(self, db_session: AsyncSession):
        self._pattern_repo = UserActivityPatternRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)

    async def update_patterns(self, user_id: int) -> UserActivityPattern:
        """Update user's activity patterns based on recent history."""
        # Get last 30 days of swipe history
        swipes = await self._get_recent_swipes(user_id, days=STREAK_CHECK_DAYS)

        if not swipes:
            return await self._pattern_repo.get_or_create(user_id)

        # Calculate most active hour
        hour_counts = self._count_by_hour(swipes)
        most_active_hour = max(hour_counts.keys(), key=lambda h: hour_counts[h]) if hour_counts else 18

        # Calculate most active day
        day_counts = self._count_by_day(swipes)
        most_active_day = max(day_counts.keys(), key=lambda d: day_counts[d]) if day_counts else 0

        # Calculate average daily swipes
        avg_daily_swipes = len(swipes) / STREAK_CHECK_DAYS

        # Update pattern
        pattern = await self._pattern_repo.get_or_create(user_id)
        pattern.most_active_hour = most_active_hour
        pattern.most_active_day = most_active_day
        pattern.avg_daily_swipes = avg_daily_swipes

        return pattern

    async def _get_recent_swipes(self, user_id: int, days: int) -> list[SwipeHistory]:
        """Get swipe history for user in last N days."""
        cutoff = utc_now() - timedelta(days=days)

        result = await self._pattern_repo.session.execute(
            select(SwipeHistory)
            .where(SwipeHistory.user_id == user_id)
            .where(SwipeHistory.swiped_at >= cutoff)
            .order_by(SwipeHistory.swiped_at.desc())
        )
        return result.scalars().all()

    def _count_by_hour(self, swipes: list[SwipeHistory]) -> dict[int, int]:
        """Count swipes by hour of day."""
        counts: dict[int, int] = dict.fromkeys(range(24), 0)

        for swipe in swipes:
            hour = swipe.swiped_at.hour
            counts[hour] += 1

        return counts

    def _count_by_day(self, swipes: list[SwipeHistory]) -> dict[int, int]:
        """Count swipes by day of week (0=Monday, 6=Sunday)."""
        counts: dict[int, int] = dict.fromkeys(range(7), 0)

        for swipe in swipes:
            # Python's weekday(): 0=Monday, 6=Sunday
            day = swipe.swiped_at.weekday()
            counts[day] += 1

        return counts
