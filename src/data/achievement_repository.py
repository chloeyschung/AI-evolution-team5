"""Repository for achievement-related operations (ADV-002)."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.datetime_utils import utc_now

from .models import AchievementDefinition, UserAchievement, UserStreak


class AchievementRepository:
    """Repository for achievement definitions and user achievements."""

    def __init__(self, db_session: AsyncSession):
        """Initialize repository.

        Args:
            db_session: Async database session.
        """
        self._db = db_session

    async def get_all_definitions(
        self, achievement_type: Optional[str] = None
    ) -> List[AchievementDefinition]:
        """Get all achievement definitions.

        Args:
            achievement_type: Optional filter by type ('streak', 'volume', 'diversity', 'curation')

        Returns:
            List of achievement definitions
        """
        query = select(AchievementDefinition).where(AchievementDefinition.is_active == 1)

        if achievement_type:
            query = query.where(AchievementDefinition.type == achievement_type)

        query = query.order_by(AchievementDefinition.type, AchievementDefinition.trigger_value)

        result = await self._db.execute(query)
        return result.scalars().all()

    async def get_definition_by_key(self, key: str) -> Optional[AchievementDefinition]:
        """Get achievement definition by key.

        Args:
            key: Achievement key (e.g., 'streak_7', 'volume_100')

        Returns:
            Achievement definition or None
        """
        result = await self._db.execute(
            select(AchievementDefinition).where(AchievementDefinition.key == key)
        )
        return result.scalar_one_or_none()

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all unlocked achievements for a user.

        Args:
            user_id: User ID

        Returns:
            List of user achievements
        """
        result = await self._db.execute(
            select(UserAchievement)
            .join(AchievementDefinition)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
        )
        return result.scalars().all()

    async def get_user_achievement(
        self, user_id: int, achievement_id: int
    ) -> Optional[UserAchievement]:
        """Get specific achievement for a user.

        Args:
            user_id: User ID
            achievement_id: Achievement definition ID

        Returns:
            User achievement or None
        """
        result = await self._db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        return result.scalar_one_or_none()

    async def award_achievement(
        self, user_id: int, achievement_id: int, metadata: Optional[dict] = None
    ) -> Optional[UserAchievement]:
        """Award an achievement to a user (idempotent).

        Args:
            user_id: User ID
            achievement_id: Achievement definition ID
            metadata: Optional metadata JSON

        Returns:
            User achievement if newly awarded, None if already unlocked
        """
        # Check if already unlocked
        existing = await self.get_user_achievement(user_id, achievement_id)
        if existing:
            return None

        # Create new achievement
        import json

        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self._db.add(user_achievement)
        await self._db.flush()

        return user_achievement

    async def get_achievements_with_progress(
        self,
        user_id: int,
        stats: dict,
    ) -> List[dict]:
        """Get all achievements with unlock status and progress.

        Args:
            user_id: User ID
            stats: User statistics dict with keys:
                - current_streak: int
                - total_swipes: int
                - platform_count: int
                - kept_count: int

        Returns:
            List of achievement dicts with progress info
        """
        definitions = await self.get_all_definitions()
        unlocked_ids = set()

        # Get unlocked achievement IDs
        user_achievements = await self.get_user_achievements(user_id)
        for ua in user_achievements:
            unlocked_ids.add(ua.achievement_id)

        result = []
        for definition in definitions:
            progress, progress_percent = self._calculate_progress(definition, stats)
            is_unlocked = definition.id in unlocked_ids

            result.append(
                {
                    "id": definition.id,
                    "key": definition.key,
                    "type": definition.type,
                    "name": definition.name,
                    "description": definition.description,
                    "icon": definition.icon,
                    "trigger_value": definition.trigger_value,
                    "is_unlocked": is_unlocked,
                    "progress": progress,
                    "progress_percent": progress_percent,
                }
            )

        return result

    def _calculate_progress(
        self, definition: AchievementDefinition, stats: dict
    ) -> tuple[int, int]:
        """Calculate progress for an achievement.

        Args:
            definition: Achievement definition
            stats: User statistics

        Returns:
            Tuple of (current_progress, progress_percent)
        """
        if definition.type == "streak":
            current = stats.get("current_streak", 0)
        elif definition.type == "volume":
            current = stats.get("total_swipes", 0)
        elif definition.type == "diversity":
            current = stats.get("platform_count", 0)
        elif definition.type == "curation":
            current = stats.get("kept_count", 0)
        else:
            current = 0

        # Calculate percentage (capped at 100)
        percent = min(int((current / definition.trigger_value) * 100), 100) if definition.trigger_value > 0 else 100

        return current, percent


class StreakRepository:
    """Repository for user streak tracking."""

    def __init__(self, db_session: AsyncSession):
        """Initialize repository.

        Args:
            db_session: Async database session.
        """
        self._db = db_session

    async def get_or_create_streak(self, user_id: int) -> UserStreak:
        """Get or create user streak record.

        Args:
            user_id: User ID

        Returns:
            User streak record
        """
        result = await self._db.execute(
            select(UserStreak).where(UserStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()

        if not streak:
            streak = UserStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
                total_active_days=0,
            )
            self._db.add(streak)
            await self._db.flush()

        return streak

    async def update_streak(
        self, user_id: int, activity_date: date
    ) -> dict[str, int]:
        """Update streak for user's activity on a given date.

        Args:
            user_id: User ID
            activity_date: Date of activity (typically today)

        Returns:
            Dict with current_streak, longest_streak, total_active_days
        """
        streak = await self.get_or_create_streak(user_id)

        # Check if already recorded for today
        if streak.last_activity_date:
            last_date = streak.last_activity_date.date() if hasattr(streak.last_activity_date, 'date') else streak.last_activity_date
            if last_date == activity_date:
                # Already recorded today
                return {
                    "current_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak,
                    "total_active_days": streak.total_active_days,
                }

        # Calculate new streak
        new_streak = self._calculate_new_streak(streak, activity_date)

        # Update streak
        streak.current_streak = new_streak
        streak.longest_streak = max(streak.longest_streak, new_streak)
        streak.last_activity_date = datetime.combine(activity_date, datetime.min.time()).replace(tzinfo=None)
        streak.total_active_days += 1
        streak.updated_at = utc_now()

        await self._db.flush()

        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "total_active_days": streak.total_active_days,
        }

    def _calculate_new_streak(
        self, streak: UserStreak, activity_date: date
    ) -> int:
        """Calculate new streak value based on previous activity.

        Args:
            streak: Current streak record
            activity_date: Date of new activity

        Returns:
            New streak value
        """
        if not streak.last_activity_date:
            # First activity
            return 1

        last_date = streak.last_activity_date.date() if hasattr(streak.last_activity_date, 'date') else streak.last_activity_date
        days_diff = (activity_date - last_date).days

        if days_diff == 1:
            # Consecutive day
            return streak.current_streak + 1
        elif days_diff == 0:
            # Same day (shouldn't happen due to early return)
            return streak.current_streak
        else:
            # Streak broken, start over
            return 1
