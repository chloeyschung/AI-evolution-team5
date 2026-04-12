"""Pydantic schemas for API request/response validation."""

from typing import List, Optional

from pydantic import BaseModel

from src.ai.metadata_extractor import ContentType
from src.data.models import SwipeAction


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
    created_at: str


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
