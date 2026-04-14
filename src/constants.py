"""Constants and enumerations for Briefly."""

from enum import StrEnum


class ReminderFrequency(StrEnum):
    """Reminder frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ContentStatus(StrEnum):
    """Content consumption status."""
    INBOX = "inbox"
    ARCHIVED = "archived"


class Provider(StrEnum):
    """Third-party integration providers."""
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"


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
