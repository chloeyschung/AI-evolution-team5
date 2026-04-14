"""Achievement checker for gamified system (ADV-002)."""

from datetime import date
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..data.models import Content, SwipeAction, SwipeHistory, ContentStatus
from ..data.achievement_repository import AchievementRepository, StreakRepository
from ..data.repository import ContentRepository, SwipeRepository


class AchievementChecker:
    """Check and award achievements for users."""

    def __init__(self, db_session: AsyncSession):
        """Initialize achievement checker.

        Args:
            db_session: Async database session.
        """
        self._achievement_repo = AchievementRepository(db_session)
        self._streak_repo = StreakRepository(db_session)
        self._content_repo = ContentRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)

    async def check_and_award(self, user_id: int) -> List[dict]:
        """Check all achievements and award newly unlocked ones.

        Args:
            user_id: User ID

        Returns:
            List of newly unlocked achievement dicts
        """
        # Calculate user stats
        stats = await self._calculate_user_stats(user_id)

        # Check each achievement type
        new_achievements = []
        new_achievements.extend(
            await self._check_streak_achievements(user_id, stats)
        )
        new_achievements.extend(
            await self._check_volume_achievements(user_id, stats)
        )
        new_achievements.extend(
            await self._check_diversity_achievements(user_id, stats)
        )
        new_achievements.extend(
            await self._check_curation_achievements(user_id, stats)
        )

        return new_achievements

    async def _calculate_user_stats(self, user_id: int) -> dict:
        """Calculate user statistics for achievement checking.

        Args:
            user_id: User ID

        Returns:
            Dict with current_streak, total_swipes, platform_count, kept_count
        """
        # Get streak
        streak = await self._streak_repo.get_or_create_streak(user_id)

        # Get swipe history (all history for now - single user system)
        swipe_history = await self._swipe_repo.get_all_history()
        total_swipes = len(swipe_history)

        # Get unique platforms from swipe history
        platform_count = await self._get_platform_count(swipe_history)

        # Get kept count
        kept_contents = await self._content_repo.get_kept(limit=None, offset=0)
        kept_count = len(kept_contents)

        return {
            "current_streak": streak.current_streak,
            "total_swipes": total_swipes,
            "platform_count": platform_count,
            "kept_count": kept_count,
        }

    async def _get_platform_count(self, swipe_history: List[SwipeHistory]) -> int:
        """Get count of unique platforms from swipe history.

        Args:
            swipe_history: List of swipe history objects

        Returns:
            Number of unique platforms
        """
        if not swipe_history:
            return 0

        # Get all content IDs
        content_ids = [swipe.content_id for swipe in swipe_history]

        # Query all content in one go
        result = await self._swipe_repo.session.execute(
            select(Content).where(Content.id.in_(content_ids))
        )
        contents = result.scalars().all()

        platforms = set(content.platform for content in contents)
        return len(platforms)

    async def _check_streak_achievements(
        self, user_id: int, stats: dict
    ) -> List[dict]:
        """Check streak-based achievements.

        Args:
            user_id: User ID
            stats: User statistics

        Returns:
            List of newly unlocked achievements
        """
        definitions = await self._achievement_repo.get_all_definitions("streak")
        new_achievements = []

        current_streak = stats.get("current_streak", 0)

        for definition in definitions:
            if current_streak >= definition.trigger_value:
                awarded = await self._achievement_repo.award_achievement(
                    user_id,
                    definition.id,
                    {"streak_days": current_streak},
                )

                if awarded:
                    new_achievements.append(
                        {
                            "id": definition.id,
                            "name": definition.name,
                            "icon": definition.icon,
                            "unlocked_at": awarded.unlocked_at.isoformat(),
                        }
                    )

        return new_achievements

    async def _check_volume_achievements(
        self, user_id: int, stats: dict
    ) -> List[dict]:
        """Check volume-based achievements (total swipes).

        Args:
            user_id: User ID
            stats: User statistics

        Returns:
            List of newly unlocked achievements
        """
        definitions = await self._achievement_repo.get_all_definitions("volume")
        new_achievements = []

        total_swipes = stats.get("total_swipes", 0)

        for definition in definitions:
            if total_swipes >= definition.trigger_value:
                awarded = await self._achievement_repo.award_achievement(
                    user_id,
                    definition.id,
                    {"total_swipes": total_swipes},
                )

                if awarded:
                    new_achievements.append(
                        {
                            "id": definition.id,
                            "name": definition.name,
                            "icon": definition.icon,
                            "unlocked_at": awarded.unlocked_at.isoformat(),
                        }
                    )

        return new_achievements

    async def _check_diversity_achievements(
        self, user_id: int, stats: dict
    ) -> List[dict]:
        """Check diversity achievements (platform count).

        Args:
            user_id: User ID
            stats: User statistics

        Returns:
            List of newly unlocked achievements
        """
        definitions = await self._achievement_repo.get_all_definitions("diversity")
        new_achievements = []

        platform_count = stats.get("platform_count", 0)

        for definition in definitions:
            if platform_count >= definition.trigger_value:
                awarded = await self._achievement_repo.award_achievement(
                    user_id,
                    definition.id,
                    {"platform_count": platform_count},
                )

                if awarded:
                    new_achievements.append(
                        {
                            "id": definition.id,
                            "name": definition.name,
                            "icon": definition.icon,
                            "unlocked_at": awarded.unlocked_at.isoformat(),
                        }
                    )

        return new_achievements

    async def _check_curation_achievements(
        self, user_id: int, stats: dict
    ) -> List[dict]:
        """Check curation achievements (kept count).

        Args:
            user_id: User ID
            stats: User statistics

        Returns:
            List of newly unlocked achievements
        """
        definitions = await self._achievement_repo.get_all_definitions("curation")
        new_achievements = []

        kept_count = stats.get("kept_count", 0)

        for definition in definitions:
            if kept_count >= definition.trigger_value:
                awarded = await self._achievement_repo.award_achievement(
                    user_id,
                    definition.id,
                    {"kept_count": kept_count},
                )

                if awarded:
                    new_achievements.append(
                        {
                            "id": definition.id,
                            "name": definition.name,
                            "icon": definition.icon,
                            "unlocked_at": awarded.unlocked_at.isoformat(),
                        }
                    )

        return new_achievements

    async def update_streak_on_swipe(
        self, user_id: int, activity_date: date | None = None
    ) -> dict[str, int]:
        """Update user's streak after a swipe action.

        Args:
            user_id: User ID
            activity_date: Date of activity (defaults to today)

        Returns:
            Dict with current_streak, longest_streak, total_active_days
        """
        if activity_date is None:
            activity_date = date.today()

        return await self._streak_repo.update_streak(user_id, activity_date)
