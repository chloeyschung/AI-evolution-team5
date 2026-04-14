"""Repository pattern for data access operations."""

from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import case, delete, func, select, update
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
    AccountDeletion,
    ContentTag,
)


class ContentRepository:
    """Repository for Content CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        metadata: ContentMetadata,
        status: ContentStatus = ContentStatus.INBOX,
    ) -> Content:
        """Save or update content from metadata.

        Args:
            metadata: ContentMetadata to save.
            status: Content status (default: INBOX for new content).

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
            existing.thumbnail_url = metadata.thumbnail_url
            if metadata.summary is not None:
                existing.summary = metadata.summary
            existing.updated_at = utc_now()
            await self.session.commit()
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
                thumbnail_url=metadata.thumbnail_url,
                status=status,
                summary=metadata.summary,
            )
            self.session.add(content)
            await self.session.commit()
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

    async def get_pending(self, limit: int = 50, platform: str | None = None) -> List[Content]:
        """Get content that hasn't been swiped yet.

        Args:
            limit: Maximum number of results.
            platform: Optional platform filter (case-insensitive).

        Returns:
            List of Content objects that have no swipe history.
        """
        query = (
            select(Content)
            .outerjoin(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.id.is_(None))
            .order_by(Content.created_at.desc())
            .limit(limit)
        )

        if platform:
            query = query.where(Content.platform.ilike(platform))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_kept(self, limit: int = 50, offset: int = 0, platform: str | None = None) -> List[Content]:
        """Get content that was swiped Keep.

        Args:
            limit: Maximum number of results.
            offset: Pagination offset.
            platform: Optional platform filter (case-insensitive).

        Returns:
            List of Content objects that were kept, ordered by recency.
        """
        query = (
            select(Content)
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.KEEP)
            .order_by(SwipeHistory.swiped_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if platform:
            query = query.where(Content.platform.ilike(platform))

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_discarded(self, limit: int = 50, offset: int = 0, platform: str | None = None) -> List[Content]:
        """Get content that was swiped Discard.

        Args:
            limit: Maximum number of results.
            offset: Pagination offset.
            platform: Optional platform filter (case-insensitive).

        Returns:
            List of Content objects that were discarded, ordered by recency.
        """
        query = (
            select(Content)
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.DISCARD)
            .order_by(SwipeHistory.swiped_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if platform:
            query = query.where(Content.platform.ilike(platform))

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_platform_counts(self) -> List[tuple[str, int]]:
        """Get list of platforms with content counts.

        Returns:
            List of (platform, count) tuples, sorted by count descending.
        """
        result = await self.session.execute(
            select(Content.platform, func.count(Content.id))
            .group_by(Content.platform)
            .order_by(func.count(Content.id).desc())
        )
        return [(row[0], row[1]) for row in result.fetchall()]

    async def search_content(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> List[Content]:
        """Search content by title, author, or tags.

        Args:
            query: Search query string (case-insensitive).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of matching Content objects, sorted by relevance then recency.
        """
        # Build search query with OR conditions for title and author
        query_pattern = f"%{query}%"

        # Search in title and author (case-insensitive)
        query_stmt = (
            select(Content)
            .where(
                (Content.title.isnot(None)) &  # Must have title
                ((Content.title.ilike(query_pattern)) | (Content.author.ilike(query_pattern)))
            )
            .order_by(Content.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        # Execute search
        result = await self.session.execute(query_stmt)
        results = list(result.scalars().unique().all())

        return results

    async def get_stats(self) -> dict:
        """Get content statistics.

        Returns:
            Dictionary with pending, kept, discarded counts.
        """
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
            swiped_at=utc_now(),
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

    async def get_all_history(self) -> List[SwipeHistory]:
        """Get all swipe history (for achievement tracking).

        Returns:
            List of all SwipeHistory objects.
        """
        result = await self.session.execute(select(SwipeHistory))
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
        now = utc_now()
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
        """Calculate and return user statistics from swipe history (optimized: single query).

        Returns:
            Dictionary with total_swipes, total_kept, total_discarded,
            retention_rate, streak_days, first_swipe_at, last_swipe_at.
        """
        # Single query for all counts using conditional aggregation
        stats_result = await self.session.execute(
            select(
                func.count(SwipeHistory.id).label("total"),
                func.sum(case((SwipeHistory.action == SwipeAction.KEEP, 1), else_=0)).label("kept"),
                func.sum(case((SwipeHistory.action == SwipeAction.DISCARD, 1), else_=0)).label("discarded"),
                func.min(SwipeHistory.swiped_at).label("first"),
                func.max(SwipeHistory.swiped_at).label("last"),
            )
        )
        row = stats_result.fetchone()

        total_swipes = row.total or 0
        total_kept = row.kept or 0
        total_discarded = row.discarded or 0
        first_swipe_at = row.first
        last_swipe_at = row.last

        # Calculate retention rate
        retention_rate = total_kept / total_swipes if total_swipes > 0 else 0.0

        # Calculate streak using unique active dates (O(1) query instead of O(N) loop)
        streak_days = 0
        if first_swipe_at is not None:
            today = date.today()
            yesterday = today - timedelta(days=1)
            end_date = yesterday if last_swipe_at is None or last_swipe_at.date() < today else today

            # Get all unique active dates in descending order (single query)
            dates_result = await self.session.execute(
                select(func.date(SwipeHistory.swiped_at)).distinct()
                .where(
                    func.date(SwipeHistory.swiped_at) <= end_date,
                    func.date(SwipeHistory.swiped_at) >= first_swipe_at.date()
                )
                .order_by(func.date(SwipeHistory.swiped_at).desc())
            )
            # Convert database dates to Python date objects for comparison
            active_dates = {date.fromisoformat(str(row[0])) if isinstance(row[0], str) else row[0] for row in dates_result.fetchall()}

            # Count consecutive days from end_date backwards
            current_date = end_date
            while current_date in active_dates:
                streak_days += 1
                current_date -= timedelta(days=1)

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
        tag_normalized = tag.strip().lower()

        await self.session.execute(
            delete(InterestTag).where(
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

    async def get_user_by_email(self, email: str) -> UserProfile | None:
        """Get user profile by email (AUTH-002).

        Args:
            email: User email address.

        Returns:
            UserProfile if found, None otherwise.
        """
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_sub(self, google_sub: str) -> UserProfile | None:
        """Get user profile by Google sub (AUTH-002).

        Args:
            google_sub: Google user ID.

        Returns:
            UserProfile if found, None otherwise.
        """
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.google_sub == google_sub)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        google_sub: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> UserProfile:
        """Create new user profile (AUTH-002).

        Args:
            email: User email address.
            google_sub: Google user ID.
            display_name: Optional display name.
            avatar_url: Optional avatar URL.

        Returns:
            Created UserProfile.
        """
        now = utc_now()
        profile = UserProfile(
            email=email,
            google_sub=google_sub,
            display_name=display_name,
            avatar_url=avatar_url,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_last_login(self, user_id: int) -> UserProfile:
        """Update user's last login timestamp (AUTH-002).

        Args:
            user_id: User ID to update.

        Returns:
            Updated UserProfile.
        """
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            profile.last_login_at = utc_now()
            await self.session.commit()
            await self.session.refresh(profile)

        return profile


class AccountDeletionRepository:
    """Repository for account deletion tracking (AUTH-002, AUTH-004)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_account_blocked(
        self, email: str | None = None, google_sub: str | None = None
    ) -> tuple[bool, datetime | None]:
        """Check if account is blocked from re-registration (AUTH-002).

        Args:
            email: User email to check.
            google_sub: Google user ID to check.

        Returns:
            Tuple of (is_blocked, block_expires_at).
            is_blocked: True if account is within 30-day block period.
            block_expires_at: When the block expires (None if not blocked).
        """
        now = utc_now()

        # Build query conditions
        conditions = []
        if email:
            conditions.append(AccountDeletion.email == email)
        if google_sub:
            conditions.append(AccountDeletion.google_sub == google_sub)

        if not conditions:
            return False, None

        query = select(AccountDeletion).where(func.or_(*conditions))
        result = await self.session.execute(query)
        deletion = result.scalar_one_or_none()

        if not deletion:
            return False, None

        # Check if block has expired
        if deletion.block_expires_at < now:
            return False, None

        return True, deletion.block_expires_at

    async def record_account_deletion(
        self,
        email: str,
        google_sub: str | None = None,
        block_days: int = 30,
    ) -> AccountDeletion:
        """Record account deletion for 30-day re-registration block (AUTH-004).

        Args:
            email: User email address.
            google_sub: Optional Google user ID.
            block_days: Number of days to block re-registration (default: 30).

        Returns:
            Created AccountDeletion record.
        """
        now = utc_now()
        block_expires_at = now + timedelta(days=block_days)

        deletion = AccountDeletion(
            email=email,
            google_sub=google_sub,
            deleted_at=now,
            block_expires_at=block_expires_at,
        )
        self.session.add(deletion)
        await self.session.commit()
        await self.session.refresh(deletion)
        return deletion


class ContentTagRepository:
    """Repository for content tag operations (AI-003)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_tags(self, content_id: int, tags: List[str]) -> List[ContentTag]:
        """Add tags to content (optimized: single query instead of N+1).

        Args:
            content_id: Content ID to add tags to.
            tags: List of tag strings.

        Returns:
            List of created ContentTag objects.
        """
        # Fetch all existing tags for this content in one query
        result = await self.session.execute(
            select(ContentTag).where(ContentTag.content_id == content_id)
        )
        existing_tags = {t.tag.lower() for t in result.scalars().all()}

        # Build new tags (avoid duplicates)
        created_tags = []
        seen = set(existing_tags)

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in seen:
                continue  # Skip duplicates
            seen.add(tag_lower)

            content_tag = ContentTag(
                content_id=content_id,
                tag=tag_lower
            )
            self.session.add(content_tag)
            created_tags.append(content_tag)

        await self.session.commit()

        # Refresh all tags to populate IDs
        for tag in created_tags:
            await self.session.refresh(tag)

        return created_tags

    async def get_tags(self, content_id: int) -> List[str]:
        """Get all tags for content.

        Args:
            content_id: Content ID.

        Returns:
            List of tag strings.
        """
        result = await self.session.execute(
            select(ContentTag.tag)
            .where(ContentTag.content_id == content_id)
            .order_by(ContentTag.tag)
        )
        return [row[0] for row in result.fetchall()]

    async def delete_tags(self, content_id: int) -> None:
        """Delete all tags for content.

        Args:
            content_id: Content ID.
        """
        await self.session.execute(
            delete(ContentTag).where(ContentTag.content_id == content_id)
        )
        await self.session.commit()
