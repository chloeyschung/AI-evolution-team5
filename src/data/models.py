"""SQLAlchemy ORM models for Briefly storage engine."""

from datetime import datetime
from enum import Enum
from typing import Optional

import sqlalchemy
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_base, mapped_column, relationship

from src.constants import (
    AuthProvider,
    ContentStatus,
    DefaultSort,
    SwipeAction,
    Theme,
)
from src.utils.datetime_utils import utc_now

Base = declarative_base()


# SEC-003: Audit event type enum

class AuditEventType(str, Enum):
    LOGIN_SUCCESS            = "login_success"
    LOGIN_FAILURE            = "login_failure"
    LOGOUT                   = "logout"
    REFRESH_TOKEN            = "refresh_token"
    ACCOUNT_DELETE_INITIATED = "account_delete_initiated"
    ACCOUNT_DELETE_CONFIRMED = "account_delete_confirmed"
    OAUTH_CONNECT            = "oauth_connect"
    OAUTH_DISCONNECT         = "oauth_disconnect"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"


class AuditLog(Base):
    """Append-only security event log (SEC-003)."""

    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    meta       = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        sqlalchemy.Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )


class Content(Base):
    """Main content table storing ContentMetadata."""

    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), nullable=False, index=True)
    platform = Column(String(100), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)
    url = Column(Text, nullable=False, index=True)
    title = Column(String(500))
    author = Column(String(200))
    timestamp = Column(DateTime)
    summary = Column(Text, nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    status = Column(SQLEnum(ContentStatus), nullable=False, default=ContentStatus.INBOX, index=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)
    # DAT-003: Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship to swipe history
    swipe_history = relationship("SwipeHistory", back_populates="content")
    user = relationship("UserProfile", back_populates="content")

    # TODO #17 (2026-04-14): Added compound index for common query pattern (user_id + created_at)
    # Unique constraint for user_id + url combination
    __table_args__ = (
        sqlalchemy.Index("ix_content_user_created", "user_id", "created_at"),
        sqlalchemy.UniqueConstraint("user_id", "url", name="unique_user_content_url"),
    )


class SwipeHistory(Base):
    """Track user swipe actions (Keep/Discard)."""

    __tablename__ = "swipe_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=False, index=True)
    action = Column(SQLEnum(SwipeAction), nullable=False)
    swiped_at = Column(DateTime, default=utc_now, index=True)

    # Relationship to content
    content = relationship("Content", back_populates="swipe_history")
    user = relationship("UserProfile", back_populates="swipe_history")

    __table_args__ = (
        sqlalchemy.UniqueConstraint("user_id", "content_id", name="uq_swipe_user_content"),
    )


class UserProfile(Base):
    """User profile information."""

    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(
        String(320), unique=True, nullable=True, index=True
    )  # AUTH-002 (nullable for backward compatibility)
    google_sub = Column(String(100), unique=True, nullable=True, index=True)  # AUTH-002; DEPRECATED AUTH-005 — migrated to user_auth_methods
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(String(500))
    last_login_at = Column(DateTime, nullable=True, index=True)  # AUTH-002
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)
    # DAT-003: Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    content = relationship("Content", back_populates="user", cascade="all, delete-orphan")
    swipe_history = relationship("SwipeHistory", back_populates="user", cascade="all, delete-orphan")


class UserPreferences(Base):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, unique=True)
    theme = Column(SQLEnum(Theme), nullable=False, default=Theme.SYSTEM)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    daily_goal = Column(Integer, nullable=False, default=20)
    default_sort = Column(SQLEnum(DefaultSort), nullable=False, default=DefaultSort.RECENCY)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)


class InterestTag(Base):
    """User interest tags for content filtering."""

    __tablename__ = "interest_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    tag = Column(String(100), nullable=False)
    # DAT-003: Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Unique constraint for user_id + tag combination
    __table_args__ = (sqlalchemy.UniqueConstraint("user_id", "tag", name="unique_user_tag"),)


class AuthenticationToken(Base):
    """User authentication tokens for session management."""

    __tablename__ = "authentication_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), unique=True, nullable=False, index=True)
    access_token = Column(String(1000), nullable=False, index=True)
    refresh_token = Column(String(1000), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    revoked_at = Column(DateTime, nullable=True, index=True)  # For logout/account delete

    # Relationship to user profile
    user = relationship("UserProfile", backref="auth_token")


class AccountDeletion(Base):
    """Track deleted accounts for 30-day re-registration block (AUTH-002)."""

    __tablename__ = "account_deletions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    google_sub = Column(String(100), unique=True, nullable=True, index=True)
    deleted_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    block_expires_at = Column(DateTime, nullable=False, index=True)  # deleted_at + 30 days
    confirmation_token = Column(String(100), nullable=True, index=True)  # For two-step deletion


class ContentTag(Base):
    """AI-generated category tags for content (AI-003)."""

    __tablename__ = "content_tags"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=False, index=True)
    tag = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationship
    content = relationship("Content", backref="tags")

    # Unique constraint for content_id + tag combination
    __table_args__ = (sqlalchemy.UniqueConstraint("content_id", "tag", name="unique_content_tag"),)


class IntegrationTokens(Base):
    """OAuth tokens for third-party integrations (INT-001).

    Tokens are encrypted at rest using Fernet symmetric encryption.
    """

    __tablename__ = "integration_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # 'youtube', 'linkedin', etc.
    access_token = Column(Text, nullable=False)  # Encrypted at rest
    refresh_token = Column(Text, nullable=False)  # Encrypted at rest
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Unique constraint for user_id + provider combination
    __table_args__ = (sqlalchemy.UniqueConstraint("user_id", "provider", name="unique_user_provider_tokens"),)

    @classmethod
    def with_encrypted_tokens(
        cls,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> "IntegrationTokens":
        """Create IntegrationTokens with encrypted tokens.

        Args:
            user_id: User ID.
            provider: Provider name (e.g., 'youtube', 'linkedin').
            access_token: Plaintext access token.
            refresh_token: Plaintext refresh token.
            expires_at: Token expiry time.

        Returns:
            IntegrationTokens instance with encrypted tokens.
        """
        from src.utils.token_encryption import encrypt_token

        return cls(
            user_id=user_id,
            provider=provider,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token),
            expires_at=expires_at,
        )

    def get_access_token(self) -> str:
        """Get decrypted access token.

        Returns:
            Plaintext access token.
        """
        from src.utils.token_encryption import decrypt_token

        return decrypt_token(self.access_token)

    def get_refresh_token(self) -> str:
        """Get decrypted refresh token.

        Returns:
            Plaintext refresh token.
        """
        from src.utils.token_encryption import decrypt_token

        return decrypt_token(self.refresh_token)


class IntegrationSyncConfig(Base):
    """Sync configuration for integrations (INT-001)."""

    __tablename__ = "integration_sync_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # 'youtube', 'linkedin', etc.
    resource_id = Column(String(200), nullable=False, index=True)  # Playlist ID, group ID, etc.
    resource_name = Column(String(500), nullable=False)  # Human-readable name
    sync_frequency = Column(String(20), nullable=False)  # 'hourly', 'daily', 'weekly'
    is_active = Column(Boolean, nullable=False, default=True)
    last_sync_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Unique constraint for user_id + provider + resource_id combination
    __table_args__ = (sqlalchemy.UniqueConstraint("user_id", "provider", "resource_id", name="unique_sync_config"),)


class IntegrationSyncLog(Base):
    """Log of sync operations (INT-001)."""

    __tablename__ = "integration_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(200), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'partial'
    ingested_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=utc_now, nullable=False, index=True)


class OAuthState(Base):
    """Single-use CSRF tokens for OAuth flows (SEC-002).

    Generated at connect time, consumed on first valid callback.
    Prevents CSRF attacks where the state=user_id pattern is spoofable.
    """

    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    state_token = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


# ADV-002: Gamified Achievement System models


class AchievementDefinition(Base):
    """Definition of unlockable achievements (ADV-002)."""

    __tablename__ = "achievement_definitions"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False, index=True)  # 'streak_1', 'volume_10', etc.
    type = Column(String(20), nullable=False, index=True)  # 'streak', 'volume', 'diversity', 'curation'
    name = Column(String(100), nullable=False)  # 'First Steps', 'Beginner', etc.
    description = Column(String(500), nullable=False)
    icon = Column(String(20), nullable=False)  # Emoji icon
    trigger_value = Column(Integer, nullable=False)  # Days for streak, count for volume, etc.
    is_active = Column(Boolean, nullable=False, default=True)


class UserAchievement(Base):
    """User's unlocked achievements (ADV-002)."""

    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievement_definitions.id"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    metadata_json = Column(Text)  # JSON: {"streak_days": 7, "platform_count": 5, etc.}

    # Relationships
    user = relationship("UserProfile", backref="achievements")
    achievement_definition = relationship("AchievementDefinition", backref="user_achievements")

    # Unique constraint for user_id + achievement_id combination
    __table_args__ = (sqlalchemy.UniqueConstraint("user_id", "achievement_id", name="unique_user_achievement"),)


class UserStreak(Base):
    """Track user's daily activity streak (ADV-002)."""

    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), unique=True, nullable=False, index=True)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    total_active_days = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    # Relationship
    user = relationship("UserProfile", backref="streak")


# ADV-003: Smart Reminders models


class ReminderPreference(Base):
    """User's reminder preferences (ADV-003)."""

    __tablename__ = "reminder_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), unique=True, nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    preferred_time = Column(DateTime)  # Preferred reminder time (e.g., 18:00:00)
    frequency = Column(String(20), nullable=False, default="daily")  # 'daily', 'weekly', 'never'
    quiet_hours_start = Column(DateTime)  # Don't remind before this time (e.g., 22:00:00)
    quiet_hours_end = Column(DateTime)  # Don't remind after this time (e.g., 08:00:00)
    backlog_threshold = Column(Integer, nullable=False, default=10)  # Items before backlog reminder
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    # Relationship
    user = relationship("UserProfile", backref="reminder_preferences")


class ReminderLog(Base):
    """Log of sent reminders and user responses (ADV-003)."""

    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), nullable=False, index=True)
    reminder_type = Column(String(50), nullable=False, index=True)  # 'backlog', 'streak', 'time_based', 'reengagement'
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    action_taken = Column(Integer, nullable=False, default=0)  # SQLite boolean
    action_taken_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("UserProfile", backref="reminder_logs")


class UserActivityPattern(Base):
    """Learned user activity patterns for optimal reminder timing (ADV-003)."""

    __tablename__ = "user_activity_patterns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id"), unique=True, nullable=False, index=True)
    most_active_hour = Column(Integer)  # 0-23, hour with most activity
    most_active_day = Column(Integer)  # 0-6, day of week with most activity (0=Monday)
    avg_daily_swipes = Column(Float, nullable=False, default=0.0)
    avg_session_duration = Column(Float, nullable=False, default=0.0)  # Minutes
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    # Relationship
    user = relationship("UserProfile", backref="activity_pattern")


# ── AUTH-005: Identity table + token tables ───────────────────────────────────

class UserAuthMethod(Base):
    """Per-provider identity row for a user (AUTH-005).

    One row per (user, provider). Replaces UserProfile.google_sub for Google
    and stores email/password credentials for email_password provider.
    """

    __tablename__ = "user_auth_methods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(SQLEnum(AuthProvider), nullable=False, index=True)
    # OAuth: provider's user ID (e.g. google_sub).
    # email_password: HMAC-SHA256(normalized_email, EMAIL_LOOKUP_KEY) — deterministic, indexable.
    provider_id = Column(String(500), nullable=False)
    password_hash = Column(Text, nullable=True)    # Argon2id; NULL for OAuth rows
    email_encrypted = Column(Text, nullable=True)  # Fernet-encrypted; NULL for OAuth rows
    email_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("UserProfile", backref="auth_methods")

    __table_args__ = (
        sqlalchemy.UniqueConstraint("provider", "provider_id", name="uq_auth_method_provider_id"),
    )


class EmailVerificationToken(Base):
    """Single-use email verification tokens (AUTH-005)."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class PasswordResetToken(Base):
    """Single-use password reset tokens (AUTH-005)."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
