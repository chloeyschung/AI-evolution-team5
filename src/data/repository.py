"""Repository pattern for data access operations."""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.metadata_extractor import ContentMetadata

from .models import (
    Content,
    SwipeHistory,
    SwipeAction,
    ContentStatus,
    UserProfile,
    UserPreferences,
    InterestTag,
    Theme,
    DefaultSort,
    utc_now,
)


class ContentRepository:
    """Repository for Content CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        metadata: ContentMetadata,
        status: ContentStatus = ContentStatus.INBOX,
        summary: str | None = None,
    ) -> Content:
        """Save or update content from metadata.

        Args:
            metadata: ContentMetadata to save.
            status: Content status (default: INBOX for new content).
            summary: Optional summary to save (for share endpoint).

        Returns:
            The saved or updated Content object.
        """
        result = await self.session.execute(
            select(Content).where(Content.url == metadata.url)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.platform = metadata.platform
            existing.content_type = metadata.content_type.value
            existing.title = metadata.title
            existing.author = metadata.author
            existing.timestamp = metadata.timestamp
            if summary is not None:
                existing.summary = summary
            existing.updated_at = utc_now()
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            content = Content(
                platform=metadata.platform,
                content_type=metadata.content_type.value,
                url=metadata.url,
                title=metadata.title,
                author=metadata.author,
                timestamp=metadata.timestamp,
                status=status,
                summary=summary,
            )
            self.session.add(content)
            await self.session.commit()
            await self.session.refresh(content)
            return content

    async def get_by_url(self, url: str) -> Content | None:
        """Get content by URL.

        Args:
            url: The content URL.

        Returns:
            Content object if found, None otherwise.
        """
        result = await self.session.execute(
            select(Content).where(Content.url == url)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, content_id: int) -> Content | None:
        """Get content by ID.

        Args:
            content_id: The content ID.

        Returns:
            Content object if found, None otherwise.
        """
        result = await self.session.execute(
            select(Content).where(Content.id == content_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 50, offset: int = 0,
                     status: ContentStatus | None = None) -> List[Content]:
        """Get all content with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.
            status: Optional filter by content status.

        Returns:
            List of Content objects, optionally filtered by status.
        """
        query = select(Content).order_by(Content.created_at.desc()).limit(limit).offset(offset)
        if status is not None:
            query = query.where(Content.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, content_id: int, new_status: ContentStatus) -> Content:
        """Update content status (INBOX → ARCHIVED transition).

        Args:
            content_id: The content ID to update.
            new_status: The new status (ARCHIVED only, one-way transition).

        Returns:
            Updated Content object.

        Raises:
            ValueError: If content is already ARCHIVED (one-way transition).
            RuntimeError: If content not found.
        """
        result = await self.session.execute(select(Content).where(Content.id == content_id))
        content = result.scalar_one_or_none()

        if content is None:
            raise RuntimeError(f"Content with ID {content_id} not found")

        if content.status == ContentStatus.ARCHIVED and new_status == ContentStatus.INBOX:
            raise ValueError("Cannot transition from ARCHIVED to INBOX (one-way transition)")

        content.status = new_status
        content.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(content)
        return content

    async def get_pending(self, limit: int = 50) -> List[Content]:
        """Get content that hasn't been swiped yet.

        Args:
            limit: Maximum number of results.

        Returns:
            List of Content objects that have no swipe history.
        """
        result = await self.session.execute(
            select(Content)
            .outerjoin(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.id.is_(None))
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_kept(self, limit: int = 50, offset: int = 0) -> List[Content]:
        """Get content that was swiped Keep.

        Args:
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of Content objects that were kept, ordered by recency.
        """
        result = await self.session.execute(
            select(Content)
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.KEEP)
            .order_by(SwipeHistory.swiped_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def get_discarded(self, limit: int = 50, offset: int = 0) -> List[Content]:
        """Get content that was swiped Discard.

        Args:
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of Content objects that were discarded, ordered by recency.
        """
        result = await self.session.execute(
            select(Content)
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.DISCARD)
            .order_by(SwipeHistory.swiped_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def get_stats(self) -> dict:
        """Get content statistics.

        Returns:
            Dictionary with pending, kept, discarded counts.
        """
        from sqlalchemy import func

        all_count = (await self.session.execute(select(func.count(Content.id)))).scalar()
        kept_count = (
            await self.session.execute(
                select(func.count(SwipeHistory.content_id)).where(SwipeHistory.action == SwipeAction.KEEP)
            )
        ).scalar()
        discarded_count = (
            await self.session.execute(
                select(func.count(SwipeHistory.content_id)).where(SwipeHistory.action == SwipeAction.DISCARD)
            )
        ).scalar()

        return {
            "pending": all_count - kept_count - discarded_count,
            "kept": kept_count,
            "discarded": discarded_count,
        }


class SwipeRepository:
    """Repository for SwipeHistory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_swipe(
        self, content_id: int, action: SwipeAction
    ) -> SwipeHistory:
        """Record a swipe action.

        Args:
            content_id: The content ID.
            action: The swipe action (KEEP or DISCARD).
                - KEEP: Content remains INBOX
                - DISCARD: Content status changes to ARCHIVED

        Returns:
            The created SwipeHistory object.
        """
        history = SwipeHistory(
            content_id=content_id,
            action=action,
            swiped_at=datetime.now(timezone.utc),
        )
        self.session.add(history)

        # Auto-update status for DISCARD action
        if action == SwipeAction.DISCARD:
            await self._update_content_status(content_id, ContentStatus.ARCHIVED)

        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def _update_content_status(self, content_id: int, new_status: ContentStatus) -> None:
        """Helper to update content status (internal use).

        Args:
            content_id: The content ID to update.
            new_status: The new status to set.
        """
        from sqlalchemy import update

        stmt = (
            update(Content)
            .where(Content.id == content_id)
            .values(status=new_status, updated_at=utc_now())
        )
        await self.session.execute(stmt)

    async def get_history(self, content_id: int) -> List[SwipeHistory]:
        """Get swipe history for a content.

        Args:
            content_id: The content ID.

        Returns:
            List of SwipeHistory objects.
        """
        result = await self.session.execute(
            select(SwipeHistory).where(SwipeHistory.content_id == content_id)
        )
        return list(result.scalars().all())

    async def record_swipes_batch(
        self, actions: List[tuple[int, SwipeAction]]
    ) -> List[SwipeHistory]:
        """Record multiple swipe actions atomically.

        All actions succeed or all fail - no partial commits.

        Args:
            actions: List of (content_id, action) tuples.

        Returns:
            List of created SwipeHistory objects.
        """
        now = datetime.now(timezone.utc)
        histories = [
            SwipeHistory(
                content_id=content_id,
                action=action,
                swiped_at=now,
            )
            for content_id, action in actions
        ]

        self.session.add_all(histories)
        await self.session.commit()

        # Refresh each object to populate IDs
        for h in histories:
            await self.session.refresh(h)

        return histories


class UserProfileRepository:
    """Repository for user profile and preferences operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_profile(self) -> UserProfile:
        """Get existing profile or create default.

        Returns:
            UserProfile object (existing or newly created).
        """
        result = await self.session.execute(select(UserProfile).limit(1))
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = UserProfile(
                display_name=None,
                avatar_url=None,
                bio=None,
            )
            self.session.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)

        return profile

    async def update_profile(
        self, display_name: str | None = None, avatar_url: str | None = None, bio: str | None = None
    ) -> UserProfile:
        """Update profile fields.

        Args:
            display_name: Optional display name to update.
            avatar_url: Optional avatar URL to update.
            bio: Optional bio to update.

        Returns:
            Updated UserProfile object.
        """
        profile = await self.get_or_create_profile()

        if display_name is not None:
            profile.display_name = display_name
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if bio is not None:
            profile.bio = bio

        profile.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(profile)

        return profile

    async def get_preferences(self) -> UserPreferences:
        """Get user preferences with defaults.

        Returns:
            UserPreferences object (existing or newly created with defaults).
        """
        result = await self.session.execute(select(UserPreferences).where(UserPreferences.user_id == 1))
        preferences = result.scalar_one_or_none()

        if preferences is None:
            preferences = UserPreferences(
                user_id=1,
                theme=Theme.SYSTEM,
                notifications_enabled=True,
                daily_goal=20,
                default_sort=DefaultSort.RECENCY,
            )
            self.session.add(preferences)
            await self.session.commit()
            await self.session.refresh(preferences)

        return preferences

    async def update_preferences(
        self,
        theme: Theme | None = None,
        notifications_enabled: bool | None = None,
        daily_goal: int | None = None,
        default_sort: DefaultSort | None = None,
    ) -> UserPreferences:
        """Update preferences fields.

        Args:
            theme: Optional theme to update.
            notifications_enabled: Optional notifications setting to update.
            daily_goal: Optional daily goal to update.
            default_sort: Optional default sort to update.

        Returns:
            Updated UserPreferences object.
        """
        preferences = await self.get_preferences()

        if theme is not None:
            preferences.theme = theme
        if notifications_enabled is not None:
            preferences.notifications_enabled = notifications_enabled
        if daily_goal is not None:
            preferences.daily_goal = daily_goal
        if default_sort is not None:
            preferences.default_sort = default_sort

        preferences.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(preferences)

        return preferences

    async def get_statistics(self) -> dict:
        """Calculate and return user statistics from swipe history.

        Returns:
            Dictionary with total_swipes, total_kept, total_discarded,
            retention_rate, streak_days, first_swipe_at, last_swipe_at.
        """
        from sqlalchemy import func
        from datetime import date, timedelta

        # Count total swipes
        total_result = await self.session.execute(select(func.count(SwipeHistory.id)))
        total_swipes = total_result.scalar() or 0

        # Count kept
        kept_result = await self.session.execute(
            select(func.count(SwipeHistory.id)).where(SwipeHistory.action == SwipeAction.KEEP)
        )
        total_kept = kept_result.scalar() or 0

        # Count discarded
        discarded_result = await self.session.execute(
            select(func.count(SwipeHistory.id)).where(SwipeHistory.action == SwipeAction.DISCARD)
        )
        total_discarded = discarded_result.scalar() or 0

        # Calculate retention rate
        retention_rate = total_kept / total_swipes if total_swipes > 0 else 0.0

        # Get first and last swipe timestamps
        first_result = await self.session.execute(
            select(func.min(SwipeHistory.swiped_at)).where(SwipeHistory.id.isnot(None))
        )
        first_swipe_at = first_result.scalar()

        last_result = await self.session.execute(
            select(func.max(SwipeHistory.swiped_at)).where(SwipeHistory.id.isnot(None))
        )
        last_swipe_at = last_result.scalar()

        # Calculate streak (consecutive days with activity, ending today or yesterday)
        streak_days = 0
        if first_swipe_at is not None:
            today = date.today()
            yesterday = today - timedelta(days=1)
            current_date = yesterday if last_swipe_at is None or last_swipe_at.date() < today else today

            while current_date >= first_swipe_at.date():
                # Check if there's any swipe on this date
                date_start = datetime.combine(current_date, datetime.min.time().replace(tzinfo=timezone.utc))
                date_end = datetime.combine(current_date, datetime.max.time().replace(tzinfo=timezone.utc))

                streak_result = await self.session.execute(
                    select(func.count(SwipeHistory.id)).where(
                        SwipeHistory.swiped_at >= date_start, SwipeHistory.swiped_at <= date_end
                    )
                )
                streak_count = streak_result.scalar() or 0

                if streak_count > 0:
                    streak_days += 1
                    current_date -= timedelta(days=1)
                else:
                    break

        return {
            "total_swipes": total_swipes,
            "total_kept": total_kept,
            "total_discarded": total_discarded,
            "retention_rate": retention_rate,
            "streak_days": streak_days,
            "first_swipe_at": first_swipe_at,
            "last_swipe_at": last_swipe_at,
        }

    async def add_interest_tag(self, tag: str) -> InterestTag:
        """Add an interest tag (unique per user).

        Args:
            tag: The tag to add (case-insensitive, trimmed).

        Returns:
            InterestTag object (existing or newly created).
        """
        tag_normalized = tag.strip().lower()

        # Check if tag already exists (case-insensitive)
        result = await self.session.execute(
            select(InterestTag).where(
                InterestTag.user_id == 1, InterestTag.tag.ilike(tag_normalized)
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        # Create new tag
        interest_tag = InterestTag(user_id=1, tag=tag_normalized)
        self.session.add(interest_tag)
        await self.session.commit()
        await self.session.refresh(interest_tag)

        return interest_tag

    async def remove_interest_tag(self, tag: str) -> None:
        """Remove an interest tag.

        Args:
            tag: The tag to remove (case-insensitive).
        """
        from sqlalchemy import delete as sqla_delete

        tag_normalized = tag.strip().lower()

        await self.session.execute(
            sqla_delete(InterestTag).where(
                InterestTag.user_id == 1, InterestTag.tag.ilike(tag_normalized)
            )
        )
        await self.session.commit()

    async def get_interest_tags(self) -> List[str]:
        """Get all user interest tags.

        Returns:
            List of tag strings.
        """
        result = await self.session.execute(
            select(InterestTag.tag).where(InterestTag.user_id == 1).order_by(InterestTag.tag)
        )
        return [row[0] for row in result.fetchall()]
