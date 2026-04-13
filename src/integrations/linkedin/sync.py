"""LinkedIn sync service for Briefly."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...ai.categorizer import Categorizer
from ...ai.metadata_extractor import ContentMetadata, ContentType
from ...ai.summarizer import Summarizer
from ...data.models import utc_now
from ...data.repository import ContentRepository, ContentTagRepository
from ..repositories.integration import IntegrationRepository
from .client import LinkedInClient, LinkedInClientError
from .models import LinkedInPost, LinkedInSyncResult


class LinkedInSyncService:
    """Sync LinkedIn saved posts to Briefly."""

    # Constants
    PROVIDER = "linkedin"
    RESOURCE_ID = "saved_posts"
    PLATFORM = "LinkedIn"

    def __init__(
        self,
        db_session: AsyncSession,
    ):
        """Initialize LinkedIn sync service.

        Args:
            db_session: Async database session.
        """
        self.db_session = db_session
        self._content_repo = ContentRepository(db_session)
        self._tag_repo = ContentTagRepository(db_session)
        self._integration_repo = IntegrationRepository(db_session)
        self._summarizer = Summarizer()
        self._categorizer = Categorizer(self._summarizer)

    async def create_client(self, user_id: int) -> Optional[LinkedInClient]:
        """Create LinkedIn client with user's tokens.

        Args:
            user_id: User ID.

        Returns:
            LinkedInClient if tokens exist, None otherwise.
        """
        from .client import LinkedInClient

        tokens = await self._integration_repo.get_oauth_tokens(user_id, self.PROVIDER)
        if not tokens:
            return None

        return LinkedInClient(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )

    async def sync_saved_posts(
        self,
        user_id: int,
        client: LinkedInClient,
        since: Optional[datetime] = None,
    ) -> LinkedInSyncResult:
        """Sync saved posts from LinkedIn.

        Args:
            user_id: User ID.
            client: LinkedIn client instance.
            since: Only sync posts saved after this time.

        Returns:
            Sync result with ingested/skipped/error counts.

        Raises:
            LinkedInClientError: If sync fails due API error.
        """
        from .client import LinkedInClient

        result = LinkedInSyncResult()

        try:
            # Get saved items from LinkedIn
            saved_items = await client.get_saved_items(count=50)

            # Filter by timestamp if provided
            if since:
                saved_items = [item for item in saved_items if item.saved_at > since]

            # Process each saved item
            for item in saved_items:
                try:
                    # Generate URL from URN
                    url = client.generate_post_url(item.target_urn)

                    # Check if already exists
                    existing = await self._content_repo.get_by_url(url)
                    if existing:
                        result.skipped += 1
                        continue

                    # Fetch post data from URL
                    post = await client.get_post_from_url(url)
                    if not post:
                        result.errors.append({
                            "urn": item.target_urn,
                            "error": "Failed to fetch post data",
                        })
                        continue

                    # Process the post
                    content_id = await self._process_post(post)
                    if content_id is not None:
                        result.ingested += 1
                    else:
                        result.errors.append({
                            "urn": item.target_urn,
                            "error": "Failed to process post",
                        })

                except Exception as e:
                    result.errors.append({
                        "urn": item.target_urn,
                        "error": str(e),
                    })

            # Update sync timestamp
            await self._integration_repo.update_last_sync(
                user_id=user_id,
                provider=self.PROVIDER,
                resource_id=self.RESOURCE_ID,
                sync_time=utc_now(),
            )

        except LinkedInClientError:
            # Re-raise client errors (auth, rate limit, etc.)
            raise
        except Exception as e:
            result.errors.append({
                "error": f"Sync failed: {e}",
            })

        return result

    async def _process_post(
        self,
        post: LinkedInPost,
    ) -> Optional[int]:
        """Process a LinkedIn post and save to database.

        Extracted from sync_saved_posts and sync_single_post to avoid duplication.

        Args:
            post: LinkedIn post data.

        Returns:
            Content ID if successful, None otherwise.
        """
        # Create content metadata
        metadata = ContentMetadata(
            platform=self.PLATFORM,
            content_type=ContentType.SOCIAL_POST,
            url=post.url,
            title=post.title,
            author=post.author,
            timestamp=post.published_at,
            thumbnail_url=post.image_url,
        )

        # Save content
        content = await self._content_repo.save(metadata)

        # Generate summary and tags in parallel if text content available
        if post.text_content:
            try:
                summary_task = self._summarizer.summarize(post.text_content)
                tags_task = self._categorizer.generate_tags(
                    title=post.title or "",
                    summary=post.text_content[:500],
                )

                summary, tags = await asyncio.gather(summary_task, tags_task)

                # Update content with summary and tags
                content.summary = summary
                await self._tag_repo.add_tags(content.id, tags)
                await self.db_session.commit()
            except Exception:
                # Continue even if AI processing fails
                pass

        return content.id

    async def sync_single_post(
        self,
        user_id: int,
        url: str,
        client: LinkedInClient,
    ) -> dict:
        """Sync a single LinkedIn post by URL.

        This is useful for manual imports or when API access is limited.

        Args:
            user_id: User ID.
            url: LinkedIn post URL.
            client: LinkedIn client instance.

        Returns:
            Dictionary with content_id and status.
        """
        from .client import LinkedInClient

        # Check if already exists
        existing = await self._content_repo.get_by_url(url)
        if existing:
            return {"content_id": existing.id, "status": "already_exists"}

        # Fetch post data
        post = await client.get_post_from_url(url)
        if not post:
            return {"status": "error", "error": "Failed to fetch post data"}

        # Process the post
        content_id = await self._process_post(post)
        if content_id is None:
            return {"status": "error", "error": "Failed to process post"}

        return {"content_id": content_id, "status": "success"}
