"""SQLAlchemy ORM models for Briefly storage engine."""

from datetime import datetime, timezone
from enum import Enum

import sqlalchemy
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SwipeAction(str, Enum):
    """User swipe actions for content."""

    KEEP = "keep"
    DISCARD = "discard"


class Theme(str, Enum):
    """UI theme options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class DefaultSort(str, Enum):
    """Default sort order options."""

    RECENCY = "recency"
    PLATFORM = "platform"


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ContentStatus(str, Enum):
    """Content consumption status."""
    INBOX = "inbox"
    ARCHIVED = "archived"


class Content(Base):
    """Main content table storing ContentMetadata."""

    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
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

    # Relationship to swipe history
    swipe_history = relationship("SwipeHistory", back_populates="content")


class SwipeHistory(Base):
    """Track user swipe actions (Keep/Discard)."""

    __tablename__ = "swipe_history"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=False, index=True)
    action = Column(SQLEnum(SwipeAction), nullable=False)
    swiped_at = Column(DateTime, default=utc_now, index=True)

    # Relationship to content
    content = relationship("Content", back_populates="swipe_history")


class UserProfile(Base):
    """User profile information."""

    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(String(500))
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)


class UserPreferences(Base):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1, unique=True)
    theme = Column(SQLEnum(Theme), nullable=False, default=Theme.SYSTEM)
    notifications_enabled = Column(Integer, nullable=False, default=1)  # SQLite boolean as integer
    daily_goal = Column(Integer, nullable=False, default=20)
    default_sort = Column(SQLEnum(DefaultSort), nullable=False, default=DefaultSort.RECENCY)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)


class InterestTag(Base):
    """User interest tags for content filtering."""

    __tablename__ = "interest_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1)
    tag = Column(String(100), nullable=False)

    # Unique constraint for user_id + tag combination
    __table_args__ = (
        sqlalchemy.UniqueConstraint("user_id", "tag", name="unique_user_tag"),
    )
