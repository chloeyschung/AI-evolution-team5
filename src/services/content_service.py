"""Content service for business logic operations.

This module contains business logic for content operations, separating concerns
from the API layer and repository layer.
"""

from src.ai.metadata_extractor import ContentMetadata
from src.constants import ContentType
from src.data.models import Content
from src.data.repository import ContentRepository, ContentTagRepository, SwipeRepository


class ContentService:
    """Service layer for content business logic.

    This service orchestrates content creation, updates, and related operations
    while keeping business logic separate from API routes and data access.
    """

    def __init__(self, db_session):
        """Initialize content service.

        Args:
            db_session: Async database session.
        """
        self._content_repo = ContentRepository(db_session)
        self._tag_repo = ContentTagRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)

    async def create_content(
        self,
        platform: str,
        content_type: ContentType,
        url: str,
        title: str | None = None,
        author: str | None = None,
        user_id: int = 1,
    ) -> Content:
        """Create new content from raw data.

        Args:
            platform: Platform name (e.g., "YouTube", "Web").
            content_type: Type of content (article, video, etc.).
            url: Content URL.
            title: Optional title.
            author: Optional author.
            user_id: User ID to associate with content.

        Returns:
            The saved Content object.

        Note:
            This method uses upsert logic - if content with same URL exists
            for the user, it updates the existing record.
        """
        metadata = ContentMetadata(
            platform=platform,
            content_type=content_type,
            url=url,
            title=title,
            author=author,
        )

        return await self._content_repo.save(metadata, user_id=user_id)

    async def get_content_by_id(self, content_id: int) -> Content | None:
        """Get content by ID.

        Args:
            content_id: Content ID.

        Returns:
            Content object if found, None otherwise.
        """
        return await self._content_repo.get_one(content_id)

    async def get_pending_content(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Content]:
        """Get content pending swipe action.

        Args:
            user_id: User ID.
            limit: Maximum items to return.
            offset: Pagination offset.

        Returns:
            List of pending content objects.
        """
        return await self._content_repo.get_pending(user_id, limit=limit, offset=offset)

    async def get_kept_content(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Content]:
        """Get kept/archived content.

        Args:
            user_id: User ID.
            limit: Maximum items to return.
            offset: Pagination offset.

        Returns:
            List of kept content objects.
        """
        return await self._content_repo.get_kept(user_id, limit=limit, offset=offset)

    async def get_discarded_content(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Content]:
        """Get discarded content.

        Args:
            user_id: User ID.
            limit: Maximum items to return.
            offset: Pagination offset.

        Returns:
            List of discarded content objects.
        """
        return await self._content_repo.get_discarded(user_id, limit=limit, offset=offset)

    async def delete_content(self, content_id: int, user_id: int) -> bool:
        """Delete content for a user.

        Args:
            content_id: Content ID to delete.
            user_id: User ID (for ownership verification).

        Returns:
            True if deleted, False if not found or not owned by user.
        """
        return await self._content_repo.delete_content(content_id, user_id)

    async def get_content_statistics(self, user_id: int) -> dict[str, int]:
        """Get content statistics for a user.

        Args:
            user_id: User ID.

        Returns:
            Dictionary with kept, discarded, and pending counts.
        """
        return await self._content_repo.get_statistics(user_id)
