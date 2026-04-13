"""YouTube sync service for ingesting videos into Briefly."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from src.ai.summarizer import Summarizer
from src.data.models import ContentStatus
from src.data.repository import ContentRepository
from src.integrations.repositories.integration import IntegrationRepository
from src.integrations.youtube.client import YouTubeClient, YouTubeClientError
from src.integrations.youtube.models import SyncResult, YouTubeVideo


class YouTubeSyncError(Exception):
    """Base exception for YouTube sync errors."""

    pass


class YouTubeSyncService:
    """Service for syncing YouTube playlists to Briefly."""

    def __init__(
        self,
        youtube_client: YouTubeClient,
        content_repo: ContentRepository,
        integration_repo: IntegrationRepository,
        summarizer: Optional[Summarizer] = None,
    ):
        """Initialize sync service.

        Args:
            youtube_client: Configured YouTube API client
            content_repo: Content repository for saving videos
            integration_repo: Integration repository for sync state
            summarizer: Optional summarizer for generating video summaries
        """
        self.youtube = youtube_client
        self.content_repo = content_repo
        self.integration_repo = integration_repo
        self.summarizer = summarizer

    async def sync_playlist(
        self,
        user_id: int,
        playlist_id: str,
        since: Optional[datetime] = None,
    ) -> SyncResult:
        """Sync a YouTube playlist, ingesting new videos.

        Args:
            user_id: User ID for sync configuration
            playlist_id: YouTube playlist ID to sync
            since: Only sync videos published after this time

        Returns:
            SyncResult with counts and errors.

        Raises:
            YouTubeSyncError: If sync fails completely.
        """
        start_time = datetime.now(timezone.utc)
        errors = []

        try:
            # Get last sync time for this playlist
            last_sync = await self.integration_repo.get_last_sync(
                user_id, "youtube", playlist_id
            )
            effective_since = since or last_sync

            # Fetch videos from YouTube
            videos = await self.youtube.get_playlist_videos(playlist_id)

            # Filter to new videos only
            new_videos = [
                v for v in videos
                if v.published_at and v.published_at > (effective_since or datetime.min.replace(tzinfo=timezone.utc))
            ]

            if not new_videos:
                return SyncResult(ingested=0, skipped=0, errors=[], duration_seconds=0)

            # Process each video
            ingested = 0
            skipped = 0

            for video in new_videos:
                try:
                    result = await self._ingest_video(user_id, video)
                    if result == "ingested":
                        ingested += 1
                    elif result == "skipped":
                        skipped += 1

                except Exception as e:
                    errors.append({
                        "video_id": video.video_id,
                        "title": video.title,
                        "error": str(e),
                    })

            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Update last sync timestamp
            await self.integration_repo.update_last_sync(
                user_id, "youtube", playlist_id, datetime.now(timezone.utc)
            )

            return SyncResult(
                ingested=ingested,
                skipped=skipped,
                errors=errors,
                duration_seconds=duration,
            )

        except YouTubeClientError as e:
            raise YouTubeSyncError(f"YouTube API error during sync: {e}")
        except Exception as e:
            raise YouTubeSyncError(f"Unexpected error during sync: {e}")

    async def _ingest_video(
        self,
        user_id: int,
        video: YouTubeVideo,
    ) -> str:
        """Ingest a single video into Briefly.

        Args:
            user_id: User ID
            video: YouTube video to ingest

        Returns:
            'ingested' if new content was created, 'skipped' if already exists
        """
        # Build YouTube URL
        url = f"https://www.youtube.com/watch?v={video.video_id}"

        # Check if already exists
        existing = await self.content_repo.get_by_url(url)
        if existing:
            return "skipped"

        # Create content record
        content = await self.content_repo.save(
            platform="youtube",
            content_type="video",
            url=url,
            title=video.title,
            author=video.channel_title,
            timestamp=video.published_at,
            thumbnail_url=video.thumbnail_url,
            status=ContentStatus.INBOX,
        )

        # Generate summary if summarizer is available
        if self.summarizer and video.description:
            try:
                summary = await self.summarizer.summarize(
                    f"Title: {video.title}\nDescription: {video.description}",
                    video.url,
                )
                await self.content_repo.update_summary(content.id, summary)
            except Exception as e:
                # Log but don't fail - summary can be generated later
                print(f"Failed to generate summary for video {video.video_id}: {e}")

        return "ingested"

    async def sync_all_playlists(
        self,
        user_id: int,
    ) -> dict[str, SyncResult]:
        """Sync all configured playlists for a user.

        Args:
            user_id: User ID

        Returns:
            Dict mapping playlist_id to SyncResult.
        """
        # Get all active sync configs for this user
        configs = await self.integration_repo.get_sync_configs(user_id, "youtube")

        # Sync each playlist concurrently
        results = {}
        tasks = [
            self.sync_playlist(user_id, config.playlist_id)
            for config in configs
            if config.is_active
        ]

        if tasks:
            sync_results = await asyncio.gather(*tasks, return_exceptions=True)

            for config, result in zip(configs, sync_results):
                if isinstance(result, Exception):
                    results[config.playlist_id] = SyncResult(
                        ingested=0,
                        skipped=0,
                        errors=[{"error": str(result)}],
                        duration_seconds=0,
                    )
                else:
                    results[config.playlist_id] = result

        return results
