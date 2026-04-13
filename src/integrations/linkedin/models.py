"""Pydantic models for LinkedIn data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LinkedInSavedItem(BaseModel):
    """LinkedIn saved item from API."""

    urn: str = Field(..., description="LinkedIn URN for the saved item")
    saved_at: datetime = Field(..., description="When the item was saved")
    target_urn: str = Field(..., description="URN of the saved content")


class LinkedInPost(BaseModel):
    """LinkedIn post data."""

    urn: str = Field(..., description="LinkedIn URN for the post")
    url: str = Field(..., description="Public URL to the post")
    title: str = Field(..., description="Post title or first few lines")
    author: str = Field(..., description="Author name")
    author_urn: str = Field(..., description="Author LinkedIn URN")
    published_at: Optional[datetime] = Field(None, description="Post publish time")
    content_type: str = Field(default="text", description="Post type: text, article, video, image")
    text_content: Optional[str] = Field(None, description="Full text content of the post")
    image_url: Optional[str] = Field(None, description="Thumbnail image URL if available")


class LinkedInSyncResult(BaseModel):
    """Result of a LinkedIn sync operation."""

    ingested: int = Field(default=0, description="Number of posts ingested")
    skipped: int = Field(default=0, description="Number of posts skipped (already exists)")
    errors: list[dict] = Field(default_factory=list, description="List of error details")

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "ingested": self.ingested,
            "skipped": self.skipped,
            "errors": self.errors,
        }
