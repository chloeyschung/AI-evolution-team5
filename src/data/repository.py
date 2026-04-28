"""Repository pattern for data access operations.

TODO #3 (2026-04-14): Added user_id parameter to ContentRepository.save() to prevent content leakage
TODO #4 (2026-04-14): Fix limit=None handling in get_pending, get_kept, get_discarded methods
TODO #6 (2026-04-14): Fix timezone handling inconsistencies in get_statistics method
"""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.metadata_extractor import ContentMetadata

from .base_repository import BaseRepository
from .models import (
    AccountDeletion,
    AuditEventType,
    AuditLog,
    Content,
    ContentStatus,
    ContentTag,
    DefaultSort,
    InterestTag,
    SwipeAction,
    SwipeHistory,
    Theme,
    UserPreferences,
    UserProfile,
    utc_now,
)


class ContentRepository(BaseRepository[Content]):
    """Repository for Content CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def save(
        self,
        metadata: ContentMetadata,
        user_id: int,
        status: ContentStatus = ContentStatus.INBOX,
    ) -> Content:
        """Save or update content from metadata.

        Args:
            metadata: ContentMetadata to save.
            user_id: User ID to associate with content.
            status: Content status (default: INBOX for new content).

        Returns:
            The saved or updated Content object.
        """
        # TODO #3 (2026-04-14): Filter by both url and user_id to prevent content leakage
        result = await self.session.execute(
            select(Content).where(Content.url == metadata.url, Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
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
            # Create new with user_id
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
                user_id=user_id,  # TODO #3 (2026-04-14): Set user_id on new content
            )
            self.session.add(content)
            await self.session.commit()
            return content

    async def get_by_url(self, url: str, user_id: int) -> Content | None:
        """Get content by URL, scoped to the given user.

        Args:
            url: The content URL.
            user_id: The user ID to scope the lookup.

        Returns:
            Content object if found, None otherwise.
        """
        result = await self.session.execute(
            select(Content).where(Content.url == url, Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, content_id: int) -> Content | None:
        """Get content by ID (excludes soft-deleted rows).

        Args:
            content_id: The content ID.

        Returns:
            Content object if found and not soft-deleted, None otherwise.
        """
        result = await self.session.execute(
            select(Content).where(Content.id == content_id, Content.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: int,
        limit: int | None = 50,
        offset: int = 0,
        status: ContentStatus | None = None,
    ) -> list[Content]:
        """Get all content with pagination.

        Args:
            user_id: User ID to filter content by.
            limit: Maximum number of results. Set to None for unlimited.
            offset: Number of results to skip.
            status: Optional filter by content status.

        Returns:
            List of Content objects, optionally filtered by status.
        """
        # TODO #4 (2026-04-14): Build query without limit first, apply conditionally
        query = select(Content).where(Content.user_id == user_id, Content.is_deleted == False).order_by(Content.created_at.desc()).offset(offset)  # noqa: E712
        # Only apply limit if not None (SQLAlchemy .limit(None) still limits!)
        if limit is not None:
            query = query.limit(limit)
        if status is not None:
            query = query.where(Content.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self, content_id: int, new_status: ContentStatus, user_id: int | None = None
    ) -> Content:
        """Update content status (INBOX → ARCHIVED transition).

        Args:
            content_id: The content ID to update.
            new_status: The new status (ARCHIVED only, one-way transition).
            user_id: Optional user ID for ownership check.

        Returns:
            Updated Content object.

        Raises:
            ValueError: If content is already ARCHIVED (one-way transition).
            RuntimeError: If content not found or ownership mismatch.
        """
        query = select(Content).where(Content.id == content_id, Content.is_deleted == False)  # noqa: E712
        if user_id is not None:
            query = query.where(Content.user_id == user_id)
        result = await self.session.execute(query)
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

    def _build_content_query_with_filters(
        self,
        base_query: select,
        platform: str | None = None,
        tags: list[str] | None = None,
    ) -> select:
        """Apply common filters to a content query.

        Args:
            base_query: The base SQLAlchemy select query.
            platform: Optional platform filter (case-insensitive).
            tags: Optional list of AI-generated tags to filter by (F-014).

        Returns:
            The query with filters applied.
        """
        query = base_query

        if platform:
            query = query.where(Content.platform.ilike(platform))

        # F-014: Filter by AI-generated tags (ContentTag)
        if tags:
            query = query.join(ContentTag).where(ContentTag.tag.in_(tags))

        return query

    async def get_pending(
        self,
        user_id: int,
        limit: int | None = 50,
        offset: int = 0,
        platform: str | None = None,
        tags: list[str] | None = None,
        cursor_created_at: datetime | None = None,
        cursor_id: int | None = None,
    ) -> list[Content]:
        """Get content that hasn't been swiped yet.

        Args:
            user_id: User ID to filter content by.
            limit: Maximum number of results. Set to None for unlimited.
            offset: Pagination offset.
            platform: Optional platform filter (case-insensitive).
            tags: Optional list of AI-generated tags to filter by (F-014).

        Returns:
            List of Content objects that have no swipe history.
        """
        # TODO #4 (2026-04-14): Build query without limit first, apply conditionally
        base_query = (
            select(Content)
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .outerjoin(
                SwipeHistory,
                (Content.id == SwipeHistory.content_id) & (SwipeHistory.user_id == user_id),
            )
            .where(SwipeHistory.id.is_(None))
            .order_by(Content.created_at.desc(), Content.id.desc())
        )
        if cursor_created_at is not None and cursor_id is not None:
            base_query = base_query.where(
                (Content.created_at < cursor_created_at)
                | ((Content.created_at == cursor_created_at) & (Content.id < cursor_id))
            )
        else:
            base_query = base_query.offset(offset)
        # Only apply limit if not None (SQLAlchemy .limit(None) still limits!)
        if limit is not None:
            base_query = base_query.limit(limit)

        query = self._build_content_query_with_filters(base_query, platform, tags)

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_kept(
        self,
        user_id: int,
        limit: int | None = 50,
        offset: int = 0,
        platform: str | None = None,
        tags: list[str] | None = None,
        cursor_swiped_at: datetime | None = None,
        cursor_content_id: int | None = None,
    ) -> list[Content]:
        """Get content that was swiped Keep.

        Args:
            user_id: User ID to filter content by.
            limit: Maximum number of results. Set to None for unlimited.
            offset: Pagination offset.
            platform: Optional platform filter (case-insensitive).
            tags: Optional list of AI-generated tags to filter by (F-014).

        Returns:
            List of Content objects that were kept, ordered by recency.
        """
        # TODO #4 (2026-04-14): Build query without limit first, apply conditionally
        base_query = (
            select(Content, SwipeHistory.swiped_at.label("cursor_swiped_at"))
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.KEEP)
            .order_by(SwipeHistory.swiped_at.desc(), Content.id.desc())
        )
        if cursor_swiped_at is not None and cursor_content_id is not None:
            base_query = base_query.where(
                (SwipeHistory.swiped_at < cursor_swiped_at)
                | ((SwipeHistory.swiped_at == cursor_swiped_at) & (Content.id < cursor_content_id))
            )
        else:
            base_query = base_query.offset(offset)
        # Only apply limit if not None (SQLAlchemy .limit(None) still limits!)
        if limit is not None:
            base_query = base_query.limit(limit)

        query = self._build_content_query_with_filters(base_query, platform, tags)

        result = await self.session.execute(query)
        rows = result.all()
        seen_ids: set[int] = set()
        contents: list[Content] = []
        for content, cursor_swiped_at in rows:
            if content.id in seen_ids:
                continue
            setattr(content, "_cursor_swiped_at", cursor_swiped_at)
            seen_ids.add(content.id)
            contents.append(content)
        return contents

    async def get_discarded(
        self,
        user_id: int,
        limit: int | None = 50,
        offset: int = 0,
        platform: str | None = None,
        tags: list[str] | None = None,
        cursor_swiped_at: datetime | None = None,
        cursor_content_id: int | None = None,
    ) -> list[Content]:
        """Get content that was swiped Discard.

        Args:
            user_id: User ID to filter content by.
            limit: Maximum number of results. Set to None for unlimited.
            offset: Pagination offset.
            platform: Optional platform filter (case-insensitive).
            tags: Optional list of AI-generated tags to filter by (F-014).

        Returns:
            List of Content objects that were discarded, ordered by recency.
        """
        # TODO #4 (2026-04-14): Build query without limit first, apply conditionally
        base_query = (
            select(Content, SwipeHistory.swiped_at.label("cursor_swiped_at"))
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.DISCARD)
            .order_by(SwipeHistory.swiped_at.desc(), Content.id.desc())
        )
        if cursor_swiped_at is not None and cursor_content_id is not None:
            base_query = base_query.where(
                (SwipeHistory.swiped_at < cursor_swiped_at)
                | ((SwipeHistory.swiped_at == cursor_swiped_at) & (Content.id < cursor_content_id))
            )
        else:
            base_query = base_query.offset(offset)
        # Only apply limit if not None (SQLAlchemy .limit(None) still limits!)
        if limit is not None:
            base_query = base_query.limit(limit)

        query = self._build_content_query_with_filters(base_query, platform, tags)

        result = await self.session.execute(query)
        rows = result.all()
        seen_ids: set[int] = set()
        contents: list[Content] = []
        for content, cursor_swiped_at in rows:
            if content.id in seen_ids:
                continue
            setattr(content, "_cursor_swiped_at", cursor_swiped_at)
            seen_ids.add(content.id)
            contents.append(content)
        return contents

    async def get_platform_counts(self, user_id: int | None = None) -> list[tuple[str, int]]:
        """Get list of platforms with content counts.

        Args:
            user_id: Optional user ID to filter content by.

        Returns:
            List of (platform, count) tuples, sorted by count descending.
        """
        query = select(Content.platform, func.count(Content.id)).where(Content.is_deleted == False).group_by(Content.platform).order_by(  # noqa: E712
            func.count(Content.id).desc()
        )
        if user_id is not None:
            query = query.where(Content.user_id == user_id)
        result = await self.session.execute(query)
        return [(row[0], row[1]) for row in result.fetchall()]

    async def search_content(
        self,
        user_id: int,
        query: str,
        limit: int = 50,
        offset: int = 0,
        cursor_created_at: datetime | None = None,
        cursor_id: int | None = None,
    ) -> list[Content]:
        """Search content by title, author, or AI-generated tags (F-016).

        Args:
            user_id: User ID to filter content by.
            query: Search query string (case-insensitive).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of matching Content objects, sorted by recency.
        """
        # Build search query with OR conditions for title, author, and tags
        query_pattern = f"%{query}%"

        # Search in title, url, author, and AI-generated tags (case-insensitive)
        # F-016: Added ContentTag JOIN to enable tag-based search
        query_stmt = (
            select(Content)
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .outerjoin(ContentTag, Content.id == ContentTag.content_id)
            .where(
                (Content.title.ilike(query_pattern))
                | (Content.url.ilike(query_pattern))
                | (Content.author.ilike(query_pattern))
                | (ContentTag.tag.ilike(query_pattern))  # F-016: Tag search
            )
            .order_by(Content.created_at.desc(), Content.id.desc())
        )
        if cursor_created_at is not None and cursor_id is not None:
            query_stmt = query_stmt.where(
                (Content.created_at < cursor_created_at)
                | ((Content.created_at == cursor_created_at) & (Content.id < cursor_id))
            )
        else:
            query_stmt = query_stmt.offset(offset)
        query_stmt = query_stmt.limit(limit)

        # Execute search
        result = await self.session.execute(query_stmt)
        results = list(result.scalars().unique().all())

        return results

    async def get_stats(self, user_id: int | None = None) -> dict:
        """Get content statistics.

        Args:
            user_id: Optional user ID to filter content by.

        Returns:
            Dictionary with pending (inbox items), kept (KEEP swipes), discarded (DISCARD swipes).
        """
        from src.constants import ContentStatus  # avoid circular at module level

        # pending = items currently in inbox (domain-correct; not arithmetic subtraction
        # which goes negative when test runs accumulate multiple swipes per item)
        inbox_base = select(func.count()).select_from(
            select(Content)
            .where(Content.is_deleted == False, Content.status == ContentStatus.INBOX)  # noqa: E712
        )
        if user_id is not None:
            inbox_base = select(func.count()).select_from(
                select(Content)
                .where(
                    Content.is_deleted == False,  # noqa: E712
                    Content.status == ContentStatus.INBOX,
                    Content.user_id == user_id,
                )
                .subquery()
            )
        pending_count = (await self.session.execute(inbox_base)).scalar() or 0

        # kept / discarded = lifetime swipe action counts (cumulative activity metrics)
        swipe_query = select(SwipeHistory)
        if user_id is not None:
            swipe_query = swipe_query.where(SwipeHistory.user_id == user_id)

        kept_count = (
            await self.session.execute(
                select(func.count()).select_from(swipe_query.where(SwipeHistory.action == SwipeAction.KEEP).subquery())
            )
        ).scalar() or 0
        discarded_count = (
            await self.session.execute(
                select(func.count())
                .select_from(swipe_query.where(SwipeHistory.action == SwipeAction.DISCARD).subquery())
            )
        ).scalar() or 0

        return {
            "pending": pending_count,
            "kept": kept_count,
            "discarded": discarded_count,
        }

    async def count_all(
        self,
        user_id: int,
        status: ContentStatus | None = None,
        platform: str | None = None,
    ) -> int:
        """Count total non-deleted content rows for a user.

        Args:
            user_id: User ID to count content for.
            status: Optional status filter.
            platform: Optional platform filter (case-insensitive).

        Returns:
            Total count of non-deleted content rows.
        """
        query = select(func.count()).where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
        if status is not None:
            query = query.where(Content.status == status)
        if platform:
            query = query.where(Content.platform.ilike(platform))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_pending(self, user_id: int) -> int:
        """Count pending content (no swipe history) for a user.

        Args:
            user_id: User ID to count for.

        Returns:
            Total count of pending content rows.
        """
        stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .outerjoin(
                SwipeHistory,
                (Content.id == SwipeHistory.content_id) & (SwipeHistory.user_id == user_id),
            )
            .where(SwipeHistory.id.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_kept(self, user_id: int) -> int:
        """Count kept content (swiped KEEP) for a user.

        Args:
            user_id: User ID to count for.

        Returns:
            Total count of kept content rows.
        """
        stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.KEEP)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_discarded(self, user_id: int) -> int:
        """Count discarded content (swiped DISCARD) for a user.

        Args:
            user_id: User ID to count for.

        Returns:
            Total count of discarded content rows.
        """
        stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
            .join(SwipeHistory, Content.id == SwipeHistory.content_id)
            .where(SwipeHistory.action == SwipeAction.DISCARD)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_search(self, user_id: int, query: str) -> int:
        """Count total search results for a query.

        Args:
            user_id: User ID to filter content by.
            query: Search query string (case-insensitive).

        Returns:
            Total count of matching content rows.
        """
        query_pattern = f"%{query}%"
        stmt = (
            select(func.count())
            .select_from(
                select(Content.id)
                .where(Content.user_id == user_id, Content.is_deleted == False)  # noqa: E712
                .outerjoin(ContentTag, Content.id == ContentTag.content_id)
                .where(
                    (Content.title.ilike(query_pattern))
                    | (Content.url.ilike(query_pattern))
                    | (Content.author.ilike(query_pattern))
                    | (ContentTag.tag.ilike(query_pattern))
                )
                .distinct()
                .subquery()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_all_ordered(
        self,
        user_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        cursor_created_at: datetime | None = None,
        cursor_id: int | None = None,
        status: ContentStatus | None = None,
        platform: str | None = None,
    ) -> list[Content]:
        """Get all content ordered by creation date (newest first).

        Args:
            user_id: Optional user ID to filter content by.
            limit: Maximum number of results.
            offset: Pagination offset.
            status: Optional status filter (INBOX, ARCHIVED).
            platform: Optional platform filter (case-insensitive).

        Returns:
            List of Content objects ordered by created_at descending.
        """
        query = (
            select(Content)
            .where(Content.is_deleted == False)  # noqa: E712
            .order_by(Content.created_at.desc(), Content.id.desc())
        )
        if cursor_created_at is not None and cursor_id is not None:
            query = query.where(
                (Content.created_at < cursor_created_at)
                | ((Content.created_at == cursor_created_at) & (Content.id < cursor_id))
            )
        else:
            query = query.offset(offset)
        query = query.limit(limit)
        if user_id is not None:
            query = query.where(Content.user_id == user_id)
        if status is not None:
            query = query.where(Content.status == status)
        if platform:
            query = query.where(Content.platform.ilike(platform))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_content(self, content_id: int, user_id: int) -> bool:
        """Hard-delete content and related records for a user (legacy — prefer soft_delete_content).

        Args:
            content_id: Content ID to delete.
            user_id: User ID (for ownership verification).

        Returns:
            True if deleted, False if not found or not owned by user.
        """
        from sqlalchemy import delete as sql_delete

        # Check ownership (include soft-deleted rows so hard-delete can still clean them)
        result = await self.session.execute(
            select(Content).where(Content.id == content_id, Content.user_id == user_id)
        )
        content = result.scalar_one_or_none()

        if content is None:
            return False

        # Delete related records first
        await self.session.execute(
            sql_delete(ContentTag).where(ContentTag.content_id == content_id)
        )
        await self.session.execute(
            sql_delete(SwipeHistory).where(SwipeHistory.content_id == content_id)
        )

        # Delete the content
        await self.session.execute(sql_delete(Content).where(Content.id == content_id))
        await self.session.commit()

        return True

    @staticmethod
    def _soft_delete(obj) -> None:
        """Set is_deleted=True and deleted_at=utc_now() on any model instance (DAT-003)."""
        obj.is_deleted = True
        obj.deleted_at = utc_now()

    async def soft_delete_content(self, content_id: int, user_id: int) -> Content | None:
        """Soft-delete content by setting is_deleted=True (DAT-003).

        Idempotent: if already soft-deleted, returns the content unchanged.

        Args:
            content_id: Content ID to soft-delete.
            user_id: User ID (ownership verification).

        Returns:
            Content object after soft-delete, or None if not found / not owned.
        """
        # Find content (including already-deleted for idempotency)
        result = await self.session.execute(
            select(Content).where(Content.id == content_id, Content.user_id == user_id)
        )
        content = result.scalar_one_or_none()

        if content is None:
            return None

        # Idempotent: already deleted — return as-is
        if not content.is_deleted:
            self._soft_delete(content)
            await self.session.commit()
            await self.session.refresh(content)

        return content

    async def restore_content(self, content_id: int, user_id: int) -> Content:
        """Restore soft-deleted content within the 30-day recovery window (DAT-003).

        Args:
            content_id: Content ID to restore.
            user_id: User ID (ownership verification).

        Returns:
            Restored Content object.

        Raises:
            RuntimeError: If content not found or not owned by user (→ 404).
            ValueError: If recovery window has expired (→ 410).
        """
        from datetime import timezone

        RECOVERY_WINDOW_DAYS = 30

        result = await self.session.execute(
            select(Content).where(Content.id == content_id, Content.user_id == user_id, Content.is_deleted == True)  # noqa: E712
        )
        content = result.scalar_one_or_none()

        if content is None:
            raise RuntimeError(f"Content with ID {content_id} not found or not deleted")

        now = utc_now()
        # Normalise to naive UTC for comparison: SQLite stores naive datetimes;
        # utc_now() returns timezone-aware. Strip tzinfo from now for comparison.
        now_naive = now.replace(tzinfo=None)
        deleted_at = content.deleted_at
        if deleted_at is not None and deleted_at.tzinfo is not None:
            deleted_at = deleted_at.replace(tzinfo=None)

        cutoff = now_naive - timedelta(days=RECOVERY_WINDOW_DAYS)
        if deleted_at is None or deleted_at < cutoff:
            raise ValueError("recovery_window_expired")

        content.is_deleted = False
        content.deleted_at = None
        content.updated_at = now_naive
        await self.session.commit()
        await self.session.refresh(content)

        return content


class SwipeRepository(BaseRepository[SwipeHistory]):
    """Repository for SwipeHistory operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def record_swipe(
        self, content_id: int, action: SwipeAction, user_id: int
    ) -> SwipeHistory:
        """Record a swipe action (idempotent — safe for iOS retry on network timeout).

        If a SwipeHistory row already exists for (user_id, content_id), the existing
        record is returned rather than raising an error.  This handles the case where
        iOS retries a POST /swipe after a network timeout without corrupting data.

        Args:
            content_id: The content ID.
            action: The swipe action (KEEP or DISCARD).
            user_id: User ID of the swipe actor.
                - KEEP: Content remains INBOX
                - DISCARD: Content status changes to ARCHIVED

        Returns:
            The created or pre-existing SwipeHistory object.
        """
        history = SwipeHistory(
            content_id=content_id,
            action=action,
            user_id=user_id,
            swiped_at=utc_now(),
        )
        self.session.add(history)

        # Auto-update status for DISCARD action
        if action == SwipeAction.DISCARD:
            await self._update_content_status(content_id, user_id, ContentStatus.ARCHIVED)

        try:
            await self.session.commit()
            await self.session.refresh(history)
            return history
        except IntegrityError:
            # Duplicate (user_id, content_id) — iOS retry scenario.
            # Roll back the failed insert and return the existing row.
            await self.session.rollback()
            result = await self.session.execute(
                select(SwipeHistory).where(
                    SwipeHistory.user_id == user_id,
                    SwipeHistory.content_id == content_id,
                )
            )
            existing_history = result.scalar_one()

            # Retry path for DISCARD must preserve ARCHIVED status after rollback.
            if action == SwipeAction.DISCARD:
                await self._update_content_status(content_id, user_id, ContentStatus.ARCHIVED)
                await self.session.commit()

            return existing_history

    async def _update_content_status(self, content_id: int, user_id: int, new_status: ContentStatus) -> None:
        """Helper to update content status (internal use).

        Args:
            content_id: The content ID to update.
            user_id: The owner's user ID — guards against cross-user updates.
            new_status: The new status to set.
        """
        stmt = (
            update(Content)
            .where(Content.id == content_id, Content.user_id == user_id)
            .values(status=new_status, updated_at=utc_now())
        )
        await self.session.execute(stmt)

    async def get_history(self, content_id: int) -> list[SwipeHistory]:
        """Get swipe history for a content.

        Args:
            content_id: The content ID.

        Returns:
            List of SwipeHistory objects.
        """
        result = await self.session.execute(select(SwipeHistory).where(SwipeHistory.content_id == content_id))
        return list(result.scalars().all())

    async def get_all_history(
        self,
        user_id: int,
        content_id: int | None = None,
        limit: int | None = None,
    ) -> list[SwipeHistory]:
        """Get swipe history scoped to a user (for achievement/trend tracking).

        Args:
            user_id: The user whose history to retrieve.
            content_id: Optional content ID to filter by.
            limit: Optional maximum number of results.

        Returns:
            List of SwipeHistory objects belonging to the user.
        """
        stmt = select(SwipeHistory).where(SwipeHistory.user_id == user_id)
        if content_id is not None:
            stmt = stmt.where(SwipeHistory.content_id == content_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_swipes_batch(
        self, actions: list[tuple[int, SwipeAction]], user_id: int
    ) -> list[SwipeHistory]:
        """Record multiple swipe actions atomically.

        All actions succeed or all fail - no partial commits.

        Args:
            actions: List of (content_id, action) tuples.
            user_id: User ID of the swipe actor.

        Returns:
            List of created SwipeHistory objects.
        """
        now = utc_now()

        # Use INSERT OR IGNORE (on_conflict_do_nothing) so duplicate
        # (user_id, content_id) rows from iOS retries are silently skipped
        # instead of raising IntegrityError and rolling back the whole batch.
        rows = [
            {
                "content_id": content_id,
                "action": action,
                "user_id": user_id,
                "swiped_at": now,
            }
            for content_id, action in actions
        ]
        stmt = sqlite_insert(SwipeHistory).values(rows).on_conflict_do_nothing()
        await self.session.execute(stmt)

        # Mirror single-swipe logic: archive content for every DISCARD action.
        # Run unconditionally so retried DISCARDs remain idempotent.
        for content_id, action in actions:
            if action == SwipeAction.DISCARD:
                await self._update_content_status(content_id, user_id, ContentStatus.ARCHIVED)

        await self.session.commit()

        # Fetch the canonical rows (covers both newly inserted and pre-existing).
        content_ids = [content_id for content_id, _ in actions]
        result = await self.session.execute(
            select(SwipeHistory).where(
                SwipeHistory.user_id == user_id,
                SwipeHistory.content_id.in_(content_ids),
            )
        )
        return list(result.scalars().all())


class UserProfileRepository(BaseRepository[UserProfile]):
    """Repository for user profile and preferences operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_or_create_profile(self, user_id: int | None = None) -> UserProfile:
        """Get existing profile or create default.

        Args:
            user_id: Optional user ID to filter by.

        Returns:
            UserProfile object (existing or newly created).
        """
        query = select(UserProfile)
        if user_id is not None:
            query = query.where(UserProfile.id == user_id)
        result = await self.session.execute(query)
        profile = result.scalar_one_or_none()

        if profile:
            return profile

        # Create default profile
        profile = UserProfile(
            display_name=None,
            avatar_url=None,
            bio=None,
            timezone="UTC",
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_profile(
        self,
        user_id: int | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        bio: str | None = None,
        timezone: str | None = None,
    ) -> UserProfile:
        """Update profile fields.

        Args:
            user_id: Optional user ID to filter by.
            display_name: Optional display name to update.
            avatar_url: Optional avatar URL to update.
            bio: Optional bio to update.
            timezone: Optional timezone to update.

        Returns:
            Updated UserProfile object.
        """
        profile = await self.get_or_create_profile(user_id=user_id)

        if display_name is not None:
            profile.display_name = display_name
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if bio is not None:
            profile.bio = bio
        if timezone is not None:
            profile.timezone = timezone

        profile.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(profile)

        return profile

    async def get_preferences(self, user_id: int) -> UserPreferences:
        """Get user preferences with defaults.

        Args:
            user_id: The user ID to get preferences for.

        Returns:
            UserPreferences object (existing or newly created with defaults).
        """
        result = await self.session.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
        preferences = result.scalar_one_or_none()

        if preferences is None:
            preferences = UserPreferences(
                user_id=user_id,
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
        user_id: int,
        theme: Theme | None = None,
        notifications_enabled: bool | None = None,
        daily_goal: int | None = None,
        default_sort: DefaultSort | None = None,
    ) -> UserPreferences:
        """Update preferences fields.

        Args:
            user_id: The user ID to update preferences for.
            theme: Optional theme to update.
            notifications_enabled: Optional notifications setting to update.
            daily_goal: Optional daily goal to update.
            default_sort: Optional default sort to update.

        Returns:
            Updated UserPreferences object.
        """
        preferences = await self.get_preferences(user_id)

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

    async def get_statistics(self, user_id: int) -> dict:
        """Calculate and return user statistics from swipe history (optimized: single query).

        Args:
            user_id: The ID of the user whose statistics to calculate.

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
            ).where(SwipeHistory.user_id == user_id)
        )
        row = stats_result.fetchone()

        total_swipes = row.total or 0
        total_kept = row.kept or 0
        total_discarded = row.discarded or 0
        first_swipe_at = row.first
        last_swipe_at = row.last

        # Calculate retention rate
        retention_rate = total_kept / total_swipes if total_swipes > 0 else 0.0

        # Streak calculation: hybrid SQL + Python walk (BE-006 assessed 2026-04-17)
        # Approach: fetch bounded set of distinct active dates via SQL, then walk backwards in Python.
        #
        # A pure-SQL recursive CTE was evaluated as an alternative:
        #   WITH RECURSIVE streak(d, cnt) AS (
        #     SELECT ?, 1
        #     UNION ALL
        #     SELECT DATE(d, '-1 day'), cnt+1 FROM streak
        #     WHERE DATE(d, '-1 day') IN (SELECT DISTINCT DATE(swiped_at) ...)
        #   )
        #   SELECT MAX(cnt) FROM streak;
        #
        # Decision: recursive CTE is more complex and not meaningfully more efficient.
        # SQLite must still scan the same date rows either way. The hybrid is already
        # well-bounded (query is capped to [first_swipe_date, end_date]) and the Python
        # loop does O(1) set lookups stopping at the first gap. This is the right tradeoff.
        streak_days = 0
        if first_swipe_at is not None:
            # Convert to UTC first to ensure consistent date comparison
            from src.utils.datetime_utils import convert_to_utc, utc_now

            first_swipe_utc = convert_to_utc(first_swipe_at)
            last_swipe_utc = convert_to_utc(last_swipe_at) if last_swipe_at else None

            # Use UTC date for comparison to avoid timezone mismatch
            today = utc_now().date()
            yesterday = today - timedelta(days=1)
            end_date = yesterday if last_swipe_utc is None or last_swipe_utc.date() < today else today

            # Get all unique active dates bounded to [first_swipe_date, end_date] (single query)
            dates_result = await self.session.execute(
                select(func.date(SwipeHistory.swiped_at))
                .distinct()
                .where(
                    SwipeHistory.user_id == user_id,
                    func.date(SwipeHistory.swiped_at) <= end_date,
                    func.date(SwipeHistory.swiped_at) >= first_swipe_utc.date(),
                )
                .order_by(func.date(SwipeHistory.swiped_at).desc())
            )
            # Convert database dates to Python date objects for O(1) set membership checks
            active_dates = {
                date.fromisoformat(str(row[0])) if isinstance(row[0], str) else row[0]
                for row in dates_result.fetchall()
            }

            # Walk backwards from end_date; stops at first gap — O(streak_length) iterations
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

    async def add_interest_tag(self, user_id: int, tag: str) -> InterestTag:
        """Add an interest tag (unique per user).

        Args:
            user_id: The user ID to add the tag for.
            tag: The tag to add (case-insensitive, trimmed).

        Returns:
            InterestTag object (existing or newly created).
        """
        tag_normalized = tag.strip().lower()

        # Check if tag already exists (case-insensitive)
        result = await self.session.execute(
            select(InterestTag).where(InterestTag.user_id == user_id, InterestTag.tag.ilike(tag_normalized))
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        # Create new tag
        interest_tag = InterestTag(user_id=user_id, tag=tag_normalized)
        self.session.add(interest_tag)
        await self.session.commit()
        await self.session.refresh(interest_tag)

        return interest_tag

    async def remove_interest_tag(self, user_id: int, tag: str) -> None:
        """Remove an interest tag.

        Args:
            user_id: The user ID to remove the tag for.
            tag: The tag to remove (case-insensitive).
        """
        tag_normalized = tag.strip().lower()

        await self.session.execute(
            delete(InterestTag).where(InterestTag.user_id == user_id, InterestTag.tag.ilike(tag_normalized))
        )
        await self.session.commit()

    async def get_interest_tags(self, user_id: int) -> list[str]:
        """Get all user interest tags.

        Args:
            user_id: The user ID to get tags for.

        Returns:
            List of tag strings.
        """
        result = await self.session.execute(
            select(InterestTag.tag).where(InterestTag.user_id == user_id).order_by(InterestTag.tag)
        )
        return [row[0] for row in result.fetchall()]

    async def get_user_by_email(self, email: str) -> UserProfile | None:
        """Get user profile by email (AUTH-002).

        Args:
            email: User email address.

        Returns:
            UserProfile if found, None otherwise. Lookup is normalized and case-insensitive.
        """
        normalized_email = email.strip().lower()
        result = await self.session.execute(
            select(UserProfile).where(func.lower(func.trim(UserProfile.email)) == normalized_email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_sub(self, google_sub: str) -> UserProfile | None:
        """Get user profile by Google sub (AUTH-002).

        Args:
            google_sub: Google user ID.

        Returns:
            UserProfile if found, None otherwise.
        """
        result = await self.session.execute(select(UserProfile).where(UserProfile.google_sub == google_sub))
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
        result = await self.session.execute(select(UserProfile).where(UserProfile.id == user_id))
        profile = result.scalar_one_or_none()

        if profile:
            profile.last_login_at = utc_now()
            await self.session.commit()
            await self.session.refresh(profile)

        return profile


class AccountDeletionRepository(BaseRepository[AccountDeletion]):
    """Repository for account deletion tracking (AUTH-002, AUTH-004)."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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

        query = select(AccountDeletion).where(or_(*conditions))
        result = await self.session.execute(query)
        deletion = result.scalar_one_or_none()

        if not deletion:
            return False, None

        # Check if block has expired
        # Normalise to naive UTC for comparison: SQLite stores naive datetimes;
        # utc_now() returns timezone-aware. Strip tzinfo from now for comparison.
        now_naive = now.replace(tzinfo=None)
        if deletion.block_expires_at < now_naive:
            return False, None

        return True, deletion.block_expires_at

    async def record_account_deletion(
        self,
        email: str,
        google_sub: str | None = None,
        block_days: int = 30,
        confirmation_token: str | None = None,
    ) -> AccountDeletion:
        """Record account deletion for 30-day re-registration block (AUTH-004).

        Args:
            email: User email address.
            google_sub: Optional Google user ID.
            block_days: Number of days to block re-registration (default: 30).
            confirmation_token: Optional token for two-step deletion confirmation.

        Returns:
            Created AccountDeletion record.
        """
        now = utc_now()
        block_expires_at = now + timedelta(days=block_days)

        # Upsert: if a record for this email already exists (e.g. step-2 of two-step
        # deletion), update it rather than inserting a duplicate (AUTH-004).
        result = await self.session.execute(
            select(AccountDeletion).where(AccountDeletion.email == email)
        )
        deletion = result.scalar_one_or_none()

        if deletion is not None:
            deletion.google_sub = google_sub
            deletion.deleted_at = now
            deletion.block_expires_at = block_expires_at
            deletion.confirmation_token = confirmation_token
        else:
            deletion = AccountDeletion(
                email=email,
                google_sub=google_sub,
                deleted_at=now,
                block_expires_at=block_expires_at,
                confirmation_token=confirmation_token,
            )
            self.session.add(deletion)

        await self.session.commit()
        await self.session.refresh(deletion)
        return deletion

    async def get_confirmation_token(self, email: str) -> str | None:
        """Get confirmation token for a pending account deletion.

        Args:
            email: User email address.

        Returns:
            Confirmation token if exists and not expired, None otherwise.
        """
        now = utc_now()
        result = await self.session.execute(
            select(AccountDeletion.confirmation_token)
            .where(AccountDeletion.email == email)
            .where(AccountDeletion.confirmation_token.isnot(None))
            .where(AccountDeletion.block_expires_at > now)
        )
        return result.scalar_one_or_none()

    async def clear_confirmation_token(self, email: str) -> bool:
        """Clear the confirmation token after successful deletion.

        Args:
            email: User email address.

        Returns:
            True if token was cleared, False if no token found.
        """
        result = await self.session.execute(
            update(AccountDeletion)
            .where(AccountDeletion.email == email)
            .where(AccountDeletion.confirmation_token.isnot(None))
            .values(confirmation_token=None)
        )
        await self.session.commit()
        return result.rowcount > 0


class ContentTagRepository(BaseRepository[ContentTag]):
    """Repository for content tag operations (AI-003)."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_tags(self, content_id: int, tags: list[str]) -> list[ContentTag]:
        """Add tags to content (optimized: single query instead of N+1).

        Args:
            content_id: Content ID to add tags to.
            tags: List of tag strings.

        Returns:
            List of created ContentTag objects.
        """
        # Fetch all existing tags for this content in one query
        result = await self.session.execute(select(ContentTag).where(ContentTag.content_id == content_id))
        existing_tags = {t.tag.lower() for t in result.scalars().all()}

        # Build new tags (avoid duplicates)
        created_tags = []
        seen = set(existing_tags)

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in seen:
                continue  # Skip duplicates
            seen.add(tag_lower)

            content_tag = ContentTag(content_id=content_id, tag=tag_lower)
            self.session.add(content_tag)
            created_tags.append(content_tag)

        await self.session.commit()

        # Refresh all tags to populate IDs
        for tag in created_tags:
            await self.session.refresh(tag)

        return created_tags

    async def get_tags(self, content_id: int) -> list[str]:
        """Get all tags for content.

        Args:
            content_id: Content ID.

        Returns:
            List of tag strings.
        """
        result = await self.session.execute(
            select(ContentTag.tag).where(ContentTag.content_id == content_id).order_by(ContentTag.tag)
        )
        return [row[0] for row in result.fetchall()]

    async def get_tags_for_content_ids(self, content_ids: list[int]) -> dict[int, list[str]]:
        """Get all tags for multiple content IDs in a single query (batch optimization).

        This method avoids N+1 query pattern by fetching all tags in one query.

        Args:
            content_ids: List of content IDs.

        Returns:
            Dictionary mapping content_id to list of tag strings.
        """
        if not content_ids:
            return {}

        # Single query to get all tags for all content IDs
        result = await self.session.execute(
            select(ContentTag.content_id, ContentTag.tag)
            .where(ContentTag.content_id.in_(content_ids))
            .order_by(ContentTag.content_id, ContentTag.tag)
        )

        # Build dictionary mapping content_id -> list of tags
        tags_by_content: dict[int, list[str]] = {}
        for row in result.fetchall():
            cid, tag = row[0], row[1]
            if cid not in tags_by_content:
                tags_by_content[cid] = []
            tags_by_content[cid].append(tag)

        return tags_by_content

    async def delete_tags(self, content_id: int) -> None:
        """Delete all tags for content.

        Args:
            content_id: Content ID.
        """
        await self.session.execute(delete(ContentTag).where(ContentTag.content_id == content_id))
        await self.session.commit()


# SEC-003: Audit Logging

class AuditRepository:
    """Append-only security event log repository (SEC-003).

    Always called with the active session so inserts participate in the
    surrounding transaction. Caller owns the commit.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Insert one audit row in the caller's transaction.

        No db.commit() here — caller owns the transaction.
        """
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type.value,
            ip_address=ip_address,
            meta=metadata,
        )
        self.db.add(entry)
