"""Pydantic models for YouTube integration."""

from datetime import datetime

from pydantic import BaseModel, Field


class YouTubeVideo(BaseModel):
    """YouTube video from API response."""

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    channel_title: str = Field(..., description="Channel name")
    channel_id: str = Field(..., description="Channel ID")
    published_at: datetime = Field(..., description="Publish timestamp")
    thumbnail_url: str | None = Field(None, description="Thumbnail URL")
    description: str | None = Field(None, description="Video description")


class YouTubePlaylist(BaseModel):
    """YouTube playlist from API response."""

    playlist_id: str = Field(..., description="Playlist ID")
    title: str = Field(..., description="Playlist title")
    description: str | None = Field(None, description="Playlist description")
    thumbnail_url: str | None = Field(None, description="Thumbnail URL")
    video_count: int = Field(default=0, description="Number of videos")
    is_watch_later: bool = Field(default=False, description="Is Watch Later playlist")


class YouTubeChannel(BaseModel):
    """YouTube channel from API response."""

    channel_id: str = Field(..., description="Channel ID")
    title: str = Field(..., description="Channel name")
    description: str | None = Field(None, description="Channel description")
    thumbnail_url: str | None = Field(None, description="Channel avatar URL")
    subscriber_count: int | None = Field(None, description="Subscriber count")


class SyncConfig(BaseModel):
    """Sync configuration for YouTube integration."""

    playlist_id: str = Field(..., description="Playlist ID to sync")
    playlist_name: str = Field(..., description="Playlist name")
    sync_frequency: str = Field(..., description="Sync frequency: hourly, daily, weekly")
    is_active: bool = Field(default=True, description="Is sync active")


class SyncResult(BaseModel):
    """Result of a sync operation."""

    ingested: int = Field(default=0, description="Number of videos ingested")
    skipped: int = Field(default=0, description="Number of videos skipped")
    errors: list[dict] = Field(default_factory=list, description="List of errors")
    duration_seconds: float = Field(default=0, description="Sync duration in seconds")


class SyncLog(BaseModel):
    """Log entry for sync operation."""

    id: int
    user_id: int
    playlist_id: str
    status: str = Field(..., description="success, failed, partial")
    ingested_count: int
    skipped_count: int
    error_message: str | None = None
    executed_at: datetime
