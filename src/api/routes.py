"""API route handlers for content and swipe operations."""

from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.metadata_extractor import ContentMetadata

from ..data.database import get_db
from ..data.models import Content, SwipeAction, SwipeHistory
from ..data.repository import ContentRepository
from .schemas import ContentCreate, ContentResponse, SwipeCreate, SwipeResponse

router = APIRouter()

SessionType = Union[AsyncSession, Session]


def _is_async_session(db: SessionType) -> bool:
    """Check if session is async."""
    return isinstance(db, AsyncSession)


@router.post("/content", status_code=201, response_model=ContentResponse)
def create_content(
    data: ContentCreate,
    db: SessionType = Depends(get_db),
) -> ContentResponse:
    """Save new content metadata."""
    metadata = ContentMetadata(
        platform=data.platform,
        content_type=data.content_type,
        url=data.url,
        title=data.title,
        author=data.author,
    )

    result = db.execute(select(Content).where(Content.url == metadata.url))
    existing = result.scalar_one_or_none()

    if existing:
        existing.platform = metadata.platform
        existing.content_type = metadata.content_type.value
        existing.title = metadata.title
        existing.author = metadata.author
        existing.timestamp = metadata.timestamp
        db.commit()
        db.refresh(existing)
        content = existing
    else:
        content = Content(
            platform=metadata.platform,
            content_type=metadata.content_type.value,
            url=metadata.url,
            title=metadata.title,
            author=metadata.author,
            timestamp=metadata.timestamp,
        )
        db.add(content)
        db.commit()
        db.refresh(content)

    return ContentResponse(
        id=content.id,
        platform=content.platform,
        content_type=content.content_type,
        url=content.url,
        title=content.title,
        author=content.author,
        created_at=content.created_at.isoformat(),
    )


@router.get("/content", response_model=list[ContentResponse])
def list_content(
    limit: int = 50,
    db: SessionType = Depends(get_db),
) -> list[ContentResponse]:
    """List all content."""
    result = db.execute(
        select(Content).order_by(Content.created_at.desc()).limit(limit)
    )
    contents = result.scalars().all()

    return [
        ContentResponse(
            id=c.id,
            platform=c.platform,
            content_type=c.content_type,
            url=c.url,
            title=c.title,
            author=c.author,
            created_at=c.created_at.isoformat(),
        )
        for c in contents
    ]


@router.post("/swipe", status_code=201, response_model=SwipeResponse)
def record_swipe(
    data: SwipeCreate,
    db: SessionType = Depends(get_db),
) -> SwipeResponse:
    """Record a swipe action."""
    history = SwipeHistory(
        content_id=data.content_id,
        action=data.action,
        swiped_at=datetime.now(timezone.utc),
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return SwipeResponse(
        id=history.id,
        content_id=history.content_id,
        action=history.action.value,
    )


@router.get("/content/pending", response_model=list[ContentResponse])
def list_pending_content(
    limit: int = Query(50, gt=0, le=100),
    db: SessionType = Depends(get_db),
) -> list[ContentResponse]:
    """Fetch content that hasn't been swiped yet.

    Returns content ordered by recency (newest first).
    """
    from sqlalchemy import outerjoin

    result = db.execute(
        select(Content)
        .outerjoin(SwipeHistory, Content.id == SwipeHistory.content_id)
        .where(SwipeHistory.id.is_(None))
        .order_by(Content.created_at.desc())
        .limit(limit)
    )
    contents = result.scalars().all()

    return [
        ContentResponse(
            id=c.id,
            platform=c.platform,
            content_type=c.content_type,
            url=c.url,
            title=c.title,
            author=c.author,
            created_at=c.created_at.isoformat(),
        )
        for c in contents
    ]
