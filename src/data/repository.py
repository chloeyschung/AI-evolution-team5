"""Repository pattern for data access operations."""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.metadata_extractor import ContentMetadata

from .models import Content, SwipeHistory, SwipeAction


class ContentRepository:
    """Repository for Content CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, metadata: ContentMetadata) -> Content:
        """Save or update content from metadata.

        Args:
            metadata: ContentMetadata to save.

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

    async def get_all(self, limit: int = 50, offset: int = 0) -> List[Content]:
        """Get all content with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Content objects.
        """
        result = await self.session.execute(
            select(Content)
            .order_by(Content.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_kept(self, limit: int = 50) -> List[Content]:
        """Get content that was swiped Keep.

        Args:
            limit: Maximum number of results.

        Returns:
            List of Content objects that were kept.
        """
        result = await self.session.execute(
            select(Content)
            .join(SwipeHistory)
            .where(SwipeHistory.action == SwipeAction.KEEP)
            .order_by(SwipeHistory.swiped_at.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

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

        Returns:
            The created SwipeHistory object.
        """
        history = SwipeHistory(
            content_id=content_id,
            action=action,
            swiped_at=datetime.now(timezone.utc),
        )
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

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
