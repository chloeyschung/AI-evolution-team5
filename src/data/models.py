"""SQLAlchemy ORM models for Briefly storage engine."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SwipeAction(str, Enum):
    """User swipe actions for content."""

    KEEP = "keep"
    DISCARD = "discard"


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


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
    created_at = Column(DateTime, default=utc_now, index=True)

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
