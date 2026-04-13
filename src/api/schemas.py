"""Pydantic schemas for API request/response validation."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.ai.metadata_extractor import ContentType
from src.data.models import SwipeAction, Theme, DefaultSort, ContentStatus


class ContentCreate(BaseModel):
    """Schema for creating new content."""

    platform: str
    content_type: ContentType
    url: str
    title: Optional[str] = None
    author: Optional[str] = None


class ContentResponse(BaseModel):
    """Schema for content response."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    content_type: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    status: ContentStatus = ContentStatus.INBOX
    created_at: str
    updated_at: Optional[str] = None


class SwipeCreate(BaseModel):
    """Schema for recording swipe action."""

    content_id: int
    action: SwipeAction


class SwipeResponse(BaseModel):
    """Schema for swipe response."""

    id: int
    content_id: int
    action: str


class SwipeActionBatch(BaseModel):
    """Single swipe action in batch."""

    content_id: int
    action: SwipeAction


class SwipeBatchRequest(BaseModel):
    """Batch swipe request."""

    actions: List[SwipeActionBatch]


class SwipeBatchResponse(BaseModel):
    """Batch swipe response."""

    recorded: int
    results: List[SwipeResponse]


class StatsResponse(BaseModel):
    """Content statistics."""

    pending: int
    kept: int
    discarded: int


class ShareRequest(BaseModel):
    """Schema for sharing content via mobile share sheet."""

    content: str = Field(..., min_length=1, description="Content to share (URL, text, etc.)")
    platform: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ShareResponse(BaseModel):
    """Schema for share response with summary."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    content_type: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    created_at: str


# UX-003: Content Detail View schemas


class SwipeHistoryResponse(BaseModel):
    """Schema for swipe history in content detail."""

    model_config = {"from_attributes": True}

    action: str
    swiped_at: str


class ContentDetailResponse(BaseModel):
    """Schema for content detail view (UX-003)."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    content_type: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    status: ContentStatus
    swipe_history: Optional[SwipeHistoryResponse] = None
    created_at: str
    updated_at: Optional[str] = None


# DAT-002: User Profile & Preferences schemas


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    model_config = {"from_attributes": True}

    id: int
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: str
    updated_at: str


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)


class UserPreferencesResponse(BaseModel):
    """Schema for user preferences response."""

    model_config = {"from_attributes": True}

    theme: Theme
    notifications_enabled: bool
    daily_goal: int
    default_sort: DefaultSort


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    theme: Optional[Theme] = None
    notifications_enabled: Optional[bool] = None
    daily_goal: Optional[int] = Field(None, gt=0, le=1000)
    default_sort: Optional[DefaultSort] = None


class UserStatisticsResponse(BaseModel):
    """Schema for user statistics response."""

    total_swipes: int
    total_kept: int
    total_discarded: int
    retention_rate: float
    streak_days: int
    first_swipe_at: Optional[str] = None
    last_swipe_at: Optional[str] = None


class InterestTagRequest(BaseModel):
    """Schema for adding an interest tag."""

    tag: str = Field(..., min_length=1, max_length=100)


class InterestTagResponse(BaseModel):
    """Schema for interest tag response."""

    model_config = {"from_attributes": True}

    id: int
    tag: str


class DeleteContentResponse(BaseModel):
    """Schema for content deletion response."""

    message: str


class PlatformCount(BaseModel):
    """Schema for platform with content count."""

    model_config = {"from_attributes": True}

    platform: str
    count: int


class ContentTagsResponse(BaseModel):
    """Schema for content tags response (AI-003)."""

    content_id: int
    tags: List[str]


# AUTH-001: Authentication schemas


class AuthStatusResponse(BaseModel):
    """Schema for authentication status check."""

    is_authenticated: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    token_expires_at: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str
    expires_at: str


class AuthError(BaseModel):
    """Schema for authentication error response."""

    error: str


# AUTH-002: Google OAuth schemas


class GoogleUserInfo(BaseModel):
    """Google user info from OAuth."""

    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    """Schema for Google login request."""

    google_id_token: str
    google_user_info: GoogleUserInfo


class GoogleLoginResponse(BaseModel):
    """Schema for Google login response."""

    access_token: str
    refresh_token: str
    expires_at: str
    user: dict  # User info
    is_new_user: bool


class LogoutResponse(BaseModel):
    """Schema for logout response."""

    message: str


class AccountDeleteRequest(BaseModel):
    """Schema for account deletion request."""

    confirm: bool = False
    confirmation_token: Optional[str] = None


class AccountDeleteResponse(BaseModel):
    """Schema for account deletion response."""

    message: str
    block_expires_at: str


# INT-001: YouTube Integration schemas


class YouTubePlaylistResponse(BaseModel):
    """Schema for YouTube playlist response."""

    model_config = {"from_attributes": True}

    playlist_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_count: int = 0
    is_watch_later: bool = False


class YouTubeConnectionStatus(BaseModel):
    """Schema for YouTube connection status."""

    is_connected: bool
    last_sync_at: Optional[str] = None


class YouTubeSyncConfigCreate(BaseModel):
    """Schema for creating sync configuration."""

    playlist_id: str = Field(..., min_length=1, max_length=200)
    playlist_name: str = Field(..., min_length=1, max_length=500)
    sync_frequency: str = Field(..., pattern="^(hourly|daily|weekly)$")


class YouTubeSyncConfigResponse(BaseModel):
    """Schema for sync configuration response."""

    model_config = {"from_attributes": True}

    playlist_id: str
    playlist_name: str
    sync_frequency: str
    is_active: bool
    last_sync_at: Optional[str] = None


class YouTubeSyncConfigUpdate(BaseModel):
    """Schema for updating sync configuration."""

    playlist_name: Optional[str] = Field(None, min_length=1, max_length=500)
    sync_frequency: Optional[str] = Field(None, pattern="^(hourly|daily|weekly)$")
    is_active: Optional[bool] = None


class YouTubeSyncLogResponse(BaseModel):
    """Schema for sync log response."""

    model_config = {"from_attributes": True}

    id: int
    playlist_id: str
    status: str
    ingested_count: int
    skipped_count: int
    error_message: Optional[str] = None
    executed_at: str


class YouTubeDisconnectResponse(BaseModel):
    """Schema for YouTube disconnect response."""

    message: str


# INT-002: LinkedIn Integration schemas


class LinkedInConnectionStatus(BaseModel):
    """Schema for LinkedIn connection status."""

    is_connected: bool
    last_sync_at: Optional[str] = None


class LinkedInSyncConfigCreate(BaseModel):
    """Schema for creating LinkedIn sync configuration."""

    resource_id: str = Field(default="saved_posts", min_length=1, max_length=200)
    resource_name: str = Field(default="Saved Posts", min_length=1, max_length=500)
    sync_frequency: str = Field(default="daily", pattern="^(hourly|daily|weekly)$")


class LinkedInSyncConfigResponse(BaseModel):
    """Schema for LinkedIn sync configuration response."""

    model_config = {"from_attributes": True}

    resource_id: str
    resource_name: str
    sync_frequency: str
    is_active: bool
    last_sync_at: Optional[str] = None


class LinkedInSyncLogResponse(BaseModel):
    """Schema for LinkedIn sync log response."""

    model_config = {"from_attributes": True}

    id: int
    resource_id: str
    status: str
    ingested_count: int
    skipped_count: int
    error_message: Optional[str] = None
    executed_at: str


class LinkedInDisconnectResponse(BaseModel):
    """Schema for LinkedIn disconnect response."""

    message: str


class LinkedInImportRequest(BaseModel):
    """Schema for manual LinkedIn post import."""

    url: str = Field(..., min_length=1, description="LinkedIn post URL")
