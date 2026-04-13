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
