"""YouTube API client with OAuth 2.0 authentication."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from google.oauth2 import credentials as google_credentials
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow

from src.integrations.youtube.models import (
    YouTubeChannel,
    YouTubePlaylist,
    YouTubeVideo,
)


class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""

    pass


class YouTubeAuthError(YouTubeClientError):
    """Authentication error with YouTube API."""

    pass


class YouTubeAPIError(YouTubeClientError):
    """API error from YouTube."""

    pass


class YouTubeClient:
    """Client for YouTube Data API v3."""

    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    OAUTH_BASE_URL = "https://accounts.google.com/o/oauth2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ):
        """Initialize YouTube client.

        Args:
            api_key: YouTube API key for unauthenticated requests
            client_id: OAuth client ID
            client_secret: OAuth client secret
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_expires_at: When access token expires
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.client_id = client_id or os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("YOUTUBE_CLIENT_SECRET")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.user_id: Optional[str] = None

        if not self.api_key:
            raise YouTubeAuthError("YouTube API key not configured")

    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            YouTubeAuthError: If token cannot be obtained or refreshed.
        """
        # Check if token is still valid (with 5 minute buffer)
        if (
            self.token_expires_at
            and datetime.now(timezone.utc)
            < self.token_expires_at - timedelta(minutes=5)
        ):
            return self.access_token or ""

        # Need to refresh token
        if not self.refresh_token:
            raise YouTubeAuthError("No refresh token available")

        new_token = await self._refresh_token()
        return new_token

    async def _refresh_token(self) -> str:
        """Refresh OAuth access token.

        Returns:
            New access token.

        Raises:
            YouTubeAuthError: If refresh fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.OAUTH_BASE_URL}/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                raise YouTubeAuthError(f"Token refresh failed: {response.text}")

            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=data.get("expires_in", 3600)
            )

            return self.access_token

    async def get_user_id(self) -> str:
        """Get authenticated user's channel ID.

        Returns:
            User's channel ID.

        Raises:
            YouTubeAuthError: If request fails.
        """
        access_token = await self.get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/channels",
                params={"part": "id", "mine": True},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise YouTubeAuthError(f"Failed to get user ID: {response.text}")

            data = response.json()
            if "items" not in data or not data["items"]:
                raise YouTubeAuthError("No channel found")

            self.user_id = data["items"][0]["id"]
            return self.user_id

    async def get_playlists(self, max_results: int = 50) -> list[YouTubePlaylist]:
        """Get user's playlists.

        Args:
            max_results: Maximum number of playlists to return.

        Returns:
            List of YouTubePlaylist objects.
        """
        access_token = await self.get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/playlists",
                params={"part": "id,snippet,contentDetails", "mine": True, "maxResults": max_results},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise YouTubeAPIError(f"Failed to get playlists: {response.text}")

            data = response.json()
            return [self._parse_playlist(p) for p in data.get("items", [])]

    async def get_playlist_videos(
        self, playlist_id: str, max_results: int = 50
    ) -> list[YouTubeVideo]:
        """Get videos in a playlist.

        Args:
            playlist_id: YouTube playlist ID.
            max_results: Maximum number of videos to return.

        Returns:
            List of YouTubeVideo objects.
        """
        access_token = await self.get_access_token()

        videos = []
        page_token: Optional[str] = None

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.API_BASE_URL}/playlistItems",
                    params={
                        "part": "snippet,contentDetails",
                        "playlistId": playlist_id,
                        "maxResults": max_results,
                        "pageToken": page_token or "",
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    raise YouTubeAPIError(f"Failed to get playlist videos: {response.text}")

                data = response.json()
                videos.extend(
                    [self._parse_video_item(p) for p in data.get("items", [])]
                )

                if "nextPageToken" not in data:
                    break
                page_token = data["nextPageToken"]

        return videos

    def _parse_playlist(self, data: dict) -> YouTubePlaylist:
        """Parse playlist data from API response."""
        snippet = data.get("snippet", {})
        content_details = data.get("contentDetails", {})

        # Check if this is the Watch Later playlist
        is_watch_later = data["id"] == "WL" or "Watch Later" in snippet.get(
            "title", ""
        )

        return YouTubePlaylist(
            playlist_id=data["id"],
            title=snippet.get("title", ""),
            description=snippet.get("description"),
            thumbnail_url=self._get_best_thumbnail(snippet.get("thumbnails")),
            video_count=content_details.get("videoCount", 0),
            is_watch_later=is_watch_later,
        )

    def _parse_video_item(self, data: dict) -> YouTubeVideo:
        """Parse video item from playlistItems response."""
        snippet = data.get("snippet", {})
        video_id = data.get("contentDetails", {}).get("videoId", "")

        return YouTubeVideo(
            video_id=video_id,
            title=snippet.get("title", ""),
            channel_title=snippet.get("channelTitle", ""),
            channel_id=snippet.get("channelId", ""),
            published_at=datetime.fromisoformat(
                snippet.get("publishedAt", "").replace("Z", "+00:00")
            ),
            thumbnail_url=self._get_best_thumbnail(snippet.get("thumbnails")),
            description=snippet.get("description"),
        )

    def _get_best_thumbnail(self, thumbnails: Optional[dict]) -> Optional[str]:
        """Get the best quality thumbnail URL."""
        if not thumbnails:
            return None

        # Prefer maxres, then standard, then high, then medium
        for quality in ["maxres", "standard", "high", "medium", "default"]:
            if quality in thumbnails:
                return thumbnails[quality].get("url")

        return None

    async def disconnect(self) -> bool:
        """Revoke OAuth tokens.

        Returns:
            True if revocation was successful.
        """
        if not self.access_token:
            return True

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": self.access_token},
            )

            return response.status_code == 200
