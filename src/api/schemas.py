"""Pydantic schemas for API request/response validation."""

from typing import Any

from pydantic import BaseModel, Field

from src.constants import (
    ContentStatus,
    ContentType,
    DefaultSort,
    SwipeAction,
    Theme,
)
from src.data.models import utc_now


class ContentCreate(BaseModel):
    """Schema for creating new content."""

    platform: str = Field(..., min_length=1, max_length=100)
    content_type: ContentType
    url: str = Field(..., min_length=1, max_length=2048, pattern=r"^https?://")
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, min_length=1, max_length=200)


class ContentStatusUpdate(BaseModel):
    """Schema for updating content status."""

    status: ContentStatus = Field(..., description="New status for the content")


class ContentResponse(BaseModel):
    """Schema for content response."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    content_type: str
    url: str
    title: str | None = None
    author: str | None = None
    summary: str | None = None
    thumbnail_url: str | None = None
    status: ContentStatus = ContentStatus.INBOX
    created_at: str
    updated_at: str | None = None

    @classmethod
    def from_content(cls, content: Any) -> "ContentResponse":
        """Create ContentResponse from Content model instance.

        Args:
            content: Content model instance from database

        Returns:
            ContentResponse instance
        """
        return cls(
            id=content.id,
            platform=content.platform,
            content_type=content.content_type,
            url=content.url,
            title=content.title,
            author=content.author,
            summary=content.summary,
            thumbnail_url=content.thumbnail_url,
            status=content.status,
            created_at=content.created_at.isoformat(),
            updated_at=content.updated_at.isoformat() if content.updated_at else None,
        )

    @classmethod
    def from_metadata(cls, metadata: Any) -> "ContentResponse":
        """Create ContentResponse from ContentMetadata instance.

        Args:
            metadata: ContentMetadata instance from service layer

        Returns:
            ContentResponse instance
        """
        return cls(
            id=metadata.id if hasattr(metadata, "id") else 0,
            platform=metadata.platform,
            content_type=metadata.content_type.value if hasattr(metadata.content_type, "value") else metadata.content_type,
            url=metadata.url,
            title=metadata.title,
            author=metadata.author,
            summary=metadata.summary if hasattr(metadata, "summary") else None,
            thumbnail_url=metadata.thumbnail_url,
            status=ContentStatus.INBOX,
            created_at=utc_now().isoformat(),
            updated_at=None,
        )


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

    actions: list[SwipeActionBatch]


class SwipeBatchResponse(BaseModel):
    """Batch swipe response."""

    recorded: int
    results: list[SwipeResponse]


class StatsResponse(BaseModel):
    """Content statistics."""

    pending: int
    kept: int
    discarded: int


class ShareRequest(BaseModel):
    """Schema for sharing content via mobile share sheet."""

    content: str = Field(..., min_length=1, description="Content to share (URL, text, etc.)")
    platform: str | None = None
    metadata: dict[str, Any] | None = None


class ShareResponse(BaseModel):
    """Schema for share response with summary."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    content_type: str
    url: str
    title: str | None = None
    author: str | None = None
    summary: str | None = None
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
    title: str | None = None
    author: str | None = None
    summary: str | None = None
    status: ContentStatus
    swipe_history: SwipeHistoryResponse | None = None
    created_at: str
    updated_at: str | None = None


# DAT-002: User Profile & Preferences schemas


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    model_config = {"from_attributes": True}

    id: int
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created_at: str
    updated_at: str


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    bio: str | None = Field(None, max_length=500)


class UserPreferencesResponse(BaseModel):
    """Schema for user preferences response."""

    model_config = {"from_attributes": True}

    theme: Theme
    notifications_enabled: bool
    daily_goal: int
    default_sort: DefaultSort


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    theme: Theme | None = None
    notifications_enabled: bool | None = None
    daily_goal: int | None = Field(None, gt=0, le=1000)
    default_sort: DefaultSort | None = None


class UserStatisticsResponse(BaseModel):
    """Schema for user statistics response."""

    total_swipes: int
    total_kept: int
    total_discarded: int
    retention_rate: float
    streak_days: int
    first_swipe_at: str | None = None
    last_swipe_at: str | None = None


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
    tags: list[str]


# AUTH-001: Authentication schemas


class AuthStatusResponse(BaseModel):
    """Schema for authentication status check."""

    is_authenticated: bool
    user_id: int | None = None
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    token_expires_at: str | None = None


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str
    refresh_token: str
    expires_at: str


class AuthError(BaseModel):
    """Schema for authentication error response."""

    error: str


class ResendVerificationRequest(BaseModel):
    """Schema for requesting email verification resend."""

    email: str


class ResendVerificationResponse(BaseModel):
    """Schema for resend verification response."""

    message: str


class EmailNotVerifiedErrorDetail(BaseModel):
    """Schema for unverified email login error details."""

    error: str
    can_resend: bool
    message: str


# AUTH-002: Google OAuth schemas


class GoogleUserInfo(BaseModel):
    """Google user info from OAuth."""

    id: str
    email: str
    name: str | None = None
    picture: str | None = None


class GoogleLoginRequest(BaseModel):
    """Schema for Google login request (ID token flow)."""

    google_id_token: str
    google_user_info: GoogleUserInfo


class GoogleOAuthCodeRequest(BaseModel):
    """Schema for Google OAuth code exchange (web flow).

    The frontend sends only the authorization code.
    The backend handles the token exchange with client_secret.
    """

    code: str


class GoogleLoginResponse(BaseModel):
    """Schema for Google login response."""

    access_token: str
    refresh_token: str
    expires_at: str
    user: "UserProfileResponse"  # User info
    is_new_user: bool


class LogoutResponse(BaseModel):
    """Schema for logout response."""

    message: str


# AUTH-005: Email/password auth schemas


class RegisterRequest(BaseModel):
    email: str
    password: str


class RegisterResponse(BaseModel):
    message: str


class VerifyEmailResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: str
    user_id: int
    email: str


class PasswordResetRequestSchema(BaseModel):
    email: str


class PasswordResetRequestResponse(BaseModel):
    message: str


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: str


class PasswordResetConfirmResponse(BaseModel):
    message: str


class LinkAccountRequest(BaseModel):
    email: str
    password: str


class LinkAccountResponse(BaseModel):
    message: str


class AccountDeleteRequest(BaseModel):
    """Schema for account deletion request."""

    confirm: bool = False
    confirmation_token: str | None = None


class AccountDeleteResponse(BaseModel):
    """Schema for account deletion response."""

    message: str
    block_expires_at: str
    confirmation_token: str | None = None


# INT-001: YouTube Integration schemas


class YouTubePlaylistResponse(BaseModel):
    """Schema for YouTube playlist response."""

    model_config = {"from_attributes": True}

    playlist_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    video_count: int = 0
    is_watch_later: bool = False


class YouTubeConnectionStatus(BaseModel):
    """Schema for YouTube connection status."""

    is_connected: bool
    last_sync_at: str | None = None


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
    last_sync_at: str | None = None


class YouTubeSyncConfigUpdate(BaseModel):
    """Schema for updating sync configuration."""

    playlist_name: str | None = Field(None, min_length=1, max_length=500)
    sync_frequency: str | None = Field(None, pattern="^(hourly|daily|weekly)$")
    is_active: bool | None = None


class YouTubeSyncLogResponse(BaseModel):
    """Schema for sync log response."""

    model_config = {"from_attributes": True}

    id: int
    playlist_id: str
    status: str
    ingested_count: int
    skipped_count: int
    error_message: str | None = None
    executed_at: str


class YouTubeDisconnectResponse(BaseModel):
    """Schema for YouTube disconnect response."""

    message: str


# INT-002: LinkedIn Integration schemas


class LinkedInConnectionStatus(BaseModel):
    """Schema for LinkedIn connection status."""

    is_connected: bool
    last_sync_at: str | None = None


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
    last_sync_at: str | None = None


class LinkedInSyncLogResponse(BaseModel):
    """Schema for LinkedIn sync log response."""

    model_config = {"from_attributes": True}

    id: int
    resource_id: str
    status: str
    ingested_count: int
    skipped_count: int
    error_message: str | None = None
    executed_at: str


class LinkedInDisconnectResponse(BaseModel):
    """Schema for LinkedIn disconnect response."""

    message: str


class LinkedInImportRequest(BaseModel):
    """Schema for manual LinkedIn post import."""

    url: str = Field(..., min_length=1, description="LinkedIn post URL")


# ADV-001: Personalized Trend Feed schemas


class TrendFeedItem(BaseModel):
    """Item in trend feed."""

    content: ContentResponse
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    matched_interests: list[str] = Field(default_factory=list, description="User interests that matched")
    top_tags: list[str] = Field(default_factory=list, max_length=3, description="Top contributing tags")


class TrendFeedResponse(BaseModel):
    """Trend feed response."""

    items: list[TrendFeedItem]
    total: int = Field(..., ge=0, description="Total matching items")
    has_more: bool = Field(..., description="Whether more items available")


# ADV-002: Gamified Achievement System schemas


class AchievementDefinitionResponse(BaseModel):
    """Schema for achievement definition."""

    model_config = {"from_attributes": True}

    id: int
    key: str
    type: str
    name: str
    description: str
    icon: str
    trigger_value: int


class AchievementProgress(BaseModel):
    """Schema for achievement with progress info."""

    id: int
    key: str
    type: str
    name: str
    description: str
    icon: str
    trigger_value: int
    is_unlocked: bool
    progress: int
    progress_percent: int
    unlocked_at: str | None = None


class AchievementsListResponse(BaseModel):
    """Schema for achievements list response."""

    achievements: list[AchievementProgress]


class StreakStats(BaseModel):
    """Schema for streak statistics."""

    current_streak: int
    longest_streak: int
    total_active_days: int


class AchievementsStatsResponse(BaseModel):
    """Schema for achievements statistics response."""

    total_unlocked: int
    total_available: int
    completion_percent: int
    streak: StreakStats
    recent_achievements: list[AchievementProgress]


class NewAchievement(BaseModel):
    """Schema for newly unlocked achievement."""

    id: int
    name: str
    icon: str
    unlocked_at: str


class CheckAchievementsResponse(BaseModel):
    """Schema for check achievements response."""

    new_achievements: list[NewAchievement]


# ADV-003: Smart Reminders schemas


class ReminderPreferencesResponse(BaseModel):
    """Schema for reminder preferences response."""

    is_enabled: bool
    preferred_time: str | None = None
    frequency: str
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    backlog_threshold: int


class ReminderPreferencesUpdate(BaseModel):
    """Schema for updating reminder preferences."""

    is_enabled: bool | None = None
    preferred_time: str | None = Field(None, max_length=20)  # "HH:MM:SS" format
    frequency: str | None = Field(None, pattern="^(daily|weekly|never)$")
    quiet_hours_start: str | None = Field(None, max_length=20)  # "HH:MM:SS" format
    quiet_hours_end: str | None = Field(None, max_length=20)  # "HH:MM:SS" format
    backlog_threshold: int | None = Field(None, gt=0, le=1000)


class ReminderSuggestionResponse(BaseModel):
    """Schema for reminder suggestion response."""

    has_reminder: bool
    reminder_type: str | None = None
    message: str | None = None
    priority: str | None = None
    metadata: dict | None = None


class ReminderRespondRequest(BaseModel):
    """Schema for responding to a reminder."""

    reminder_id: int
    action: str = Field(..., pattern="^(acted|dismissed)$")


class ReminderRespondResponse(BaseModel):
    """Schema for reminder response confirmation."""

    success: bool
    message: str
