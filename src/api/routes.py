"""API route handlers for content and swipe operations."""

from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.ai.metadata_extractor import ContentMetadata

from ..data.database import get_db
from ..data.models import Content, SwipeAction, SwipeHistory
from ..data.repository import ContentRepository, SwipeRepository
from .schemas import (
    ContentCreate,
    ContentResponse,
    SwipeCreate,
    SwipeResponse,
    SwipeBatchRequest,
    SwipeBatchResponse,
    StatsResponse,
)

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
async def list_content(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
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


@router.post("/swipe", status_code=201, response_model=Union[SwipeResponse, SwipeBatchResponse])
def record_swipe(
    data: Union[SwipeCreate, SwipeBatchRequest],
    db: SessionType = Depends(get_db),
) -> Union[SwipeResponse, SwipeBatchResponse]:
    """Record a swipe action (single or batch)."""
    if _is_async_session(db):
        repo = SwipeRepository(db)

        if isinstance(data, SwipeBatchRequest):
            import asyncio

            actions = [(a.content_id, a.action) for a in data.actions]
            histories = asyncio.get_event_loop().run_until_complete(repo.record_swipes_batch(actions))
            return SwipeBatchResponse(
                recorded=len(histories),
                results=[
                    SwipeResponse(id=h.id, content_id=h.content_id, action=h.action.value)
                    for h in histories
                ],
            )
        else:
            history = asyncio.get_event_loop().run_until_complete(repo.record_swipe(data.content_id, data.action))
            return SwipeResponse(
                id=history.id,
                content_id=history.content_id,
                action=history.action.value,
            )
    else:
        # Sync session handling
        if isinstance(data, SwipeBatchRequest):
            histories = []
            for action_batch in data.actions:
                history = SwipeHistory(
                    content_id=action_batch.content_id,
                    action=action_batch.action,
                    swiped_at=datetime.now(timezone.utc),
                )
                db.add(history)
                histories.append(history)
            db.commit()

            return SwipeBatchResponse(
                recorded=len(histories),
                results=[
                    SwipeResponse(id=h.id, content_id=h.content_id, action=h.action.value)
                    for h in histories
                ],
            )
        else:
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
    from sqlalchemy.orm import outerjoin

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


@router.get("/content/kept", response_model=list[ContentResponse])
def list_kept_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: SessionType = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Keep.

    Returns kept content ordered by swipe recency (newest first).
    """
    repo = ContentRepository(db)

    if _is_async_session(db):
        import asyncio

        contents = asyncio.get_event_loop().run_until_complete(
            repo.async_get_kept(limit=limit, offset=offset)
        )
    else:
        contents = repo.get_kept(limit=limit, offset=offset)

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


@router.get("/content/discarded", response_model=list[ContentResponse])
def list_discarded_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: SessionType = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Discard.

    Returns discarded content ordered by swipe recency (newest first).
    """
    repo = ContentRepository(db)

    if _is_async_session(db):
        import asyncio

        contents = asyncio.get_event_loop().run_until_complete(
            repo.async_get_discarded(limit=limit, offset=offset)
        )
    else:
        contents = repo.get_discarded(limit=limit, offset=offset)

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


@router.get("/stats", response_model=StatsResponse)
def get_content_stats(db: SessionType = Depends(get_db)) -> StatsResponse:
    """Get content statistics.

    Returns counts of pending, kept, and discarded content.
    """
    repo = ContentRepository(db)

    if _is_async_session(db):
        import asyncio

        stats = asyncio.get_event_loop().run_until_complete(repo.async_get_stats())
    else:
        stats = repo.get_stats()

    return StatsResponse(
        pending=stats["pending"],
        kept=stats["kept"],
        discarded=stats["discarded"],
    )
