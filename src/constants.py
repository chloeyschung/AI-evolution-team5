"""Constants and enumerations for Briefly."""

from enum import StrEnum


class SyncFrequency(StrEnum):
    """Sync frequency options for integration configs."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class ReminderFrequency(StrEnum):
    """Reminder frequency options."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NEVER = "never"


class ContentStatus(StrEnum):
    """Content consumption status."""

    INBOX = "inbox"
    ARCHIVED = "archived"


class Provider(StrEnum):
    """Third-party integration providers."""

    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"


class AuthProvider(StrEnum):
    """Authentication providers for user_auth_methods table (AUTH-005)."""

    GOOGLE = "google"
    EMAIL_PASSWORD = "email_password"
    KAKAO = "kakao"
    NAVER = "naver"
    GITHUB = "github"


class SwipeAction(StrEnum):
    """User swipe actions for content."""

    KEEP = "keep"
    DISCARD = "discard"


class Theme(StrEnum):
    """UI theme options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class DefaultSort(StrEnum):
    """Default sort order options."""

    RECENCY = "recency"
    PLATFORM = "platform"


class ContentType(StrEnum):
    """Supported content types for metadata."""

    ARTICLE = "article"
    VIDEO = "video"
    IMAGE = "image"
    SOCIAL_POST = "social_post"
    PROFILE = "profile"
    DEEP_LINK = "deep_link"


class ReminderType(StrEnum):
    """Types of reminders."""

    BACKLOG = "backlog"
    STREAK = "streak"
    TIME_BASED = "time_based"
    REENGAGEMENT = "reengagement"


class ReminderPriority(StrEnum):
    """Priority levels for reminders."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Pagination constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Swipe history limits
SWIPE_HISTORY_DAYS_FOR_STREAK = 30

# Content limits
MAX_CONTENT_SUMMARY_LENGTH = 500
MIN_CONTENT_SUMMARY_LENGTH = 50

# Rate limiting
SHARE_RATE_LIMIT = "10/minute"
INGEST_RATE_LIMIT = "30/minute"

# Tag generation limits
MAX_TAGS_PER_CONTENT = 3
MAX_TAG_LENGTH = 50

# Trend analyzer limits
TREND_FEED_MAX_LIMIT = 1000  # Hard limit to prevent memory issues
TREND_FEED_SAMPLE_SIZE = 50  # Sample size for scoring
TREND_FEED_MIN_ITEMS_FOR_SCORING = 10  # Minimum items to use scoring algorithm
TREND_FEED_DEFAULT_NEUTRAL_SCORE = 0.5  # Default score when no data available
TREND_FEED_MIN_SCORE_THRESHOLD = 0.1  # Minimum score to appear in feed

# Trend analyzer scoring weights
TREND_INTEREST_MATCH_WEIGHT = 0.35
TREND_TAG_SIMILARITY_WEIGHT = 0.30
TREND_RECENCY_WEIGHT = 0.20
TREND_ENGAGEMENT_WEIGHT = 0.15

# Time-based constants (in days)
STREAK_CHECK_DAYS = 30
ACCOUNT_DELETION_BLOCK_DAYS = 30
REMINDER_BACKLOG_THRESHOLD = 10
TREND_ANALYSIS_WEEK_CUTOFF = 7
TREND_ANALYSIS_MONTH_CUTOFF = 30
ENGAGEMENT_HALF_LIFE_DAYS = 30

# Sync frequency thresholds (in hours)
HOURLY_SYNC_THRESHOLD = 1
DAILY_SYNC_THRESHOLD = 24
WEEKLY_SYNC_THRESHOLD = 168  # 7 * 24


class ErrorCode(StrEnum):
    """Standardized error codes for API responses."""

    # Authentication errors (401)
    UNAUTHORIZED = "unauthorized"
    INVALID_REFRESH_TOKEN = "invalid_refresh_token"
    INVALID_GOOGLE_TOKEN = "invalid_google_token"

    # Not found errors (404)
    CONTENT_NOT_FOUND = "content_not_found"
    USER_NOT_FOUND = "user_not_found"
    SYNC_CONFIG_NOT_FOUND = "sync_config_not_found"

    # Integration errors (401/404)
    NOT_CONNECTED_TO_YOUTUBE = "not_connected_to_youtube"
    YOUTUBE_AUTH_EXPIRED = "youtube_auth_expired"
    NOT_CONNECTED_TO_LINKEDIN = "not_connected_to_linkedin"
    LINKEDIN_AUTH_EXPIRED = "linkedin_auth_expired"

    # Validation errors (400)
    INVALID_STATE = "invalid_state"
    INVALID_FORMAT = "invalid_format"
    INVALID_TIME_FORMAT = "invalid_time_format"
    YOUTUBE_AUTH_FAILED = "youtube_auth_failed"
    LINKEDIN_AUTH_FAILED = "linkedin_auth_failed"

    # Server errors (500)
    YOUTUBE_OAUTH_NOT_CONFIGURED = "youtube_oauth_not_configured"
    LINKEDIN_OAUTH_NOT_CONFIGURED = "linkedin_oauth_not_configured"
    FAILED_TO_GET_CONTENT_ID = "failed_to_get_content_id"
    FAILED_TO_IMPORT = "failed_to_import"
