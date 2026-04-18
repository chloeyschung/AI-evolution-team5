"""Swipe domain router — /swipe/* and /content/pending, /content/kept, /content/discarded."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.repository import ContentRepository
from ...services import SwipeService
from ..dependencies import get_current_user
from ..schemas import (
    ContentResponse,
    PaginatedContentResponse,
    SwipeBatchRequest,
    SwipeBatchResponse,
    SwipeCreate,
    SwipeResponse,
)

router = APIRouter()


@router.post("/swipe", status_code=201, response_model=SwipeResponse | SwipeBatchResponse)
async def record_swipe(
    data: SwipeCreate | SwipeBatchRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SwipeResponse | SwipeBatchResponse:
    """Record a swipe action (single or batch)."""
    service = SwipeService(db)

    if isinstance(data, SwipeBatchRequest):
        actions = [(a.content_id, a.action) for a in data.actions]
        result = await service.record_swipes_batch(actions, user_id=user_id)
        return SwipeBatchResponse(
            recorded=result.recorded,
            results=[SwipeResponse(id=r.id, content_id=r.content_id, action=r.action.value) for r in result.results],
        )
    else:
        result = await service.record_swipe(data.content_id, data.action, user_id=user_id)
        return SwipeResponse(
            id=result.id,
            content_id=result.content_id,
            action=result.action.value,
        )


@router.get("/content/pending", response_model=PaginatedContentResponse)
async def list_pending_content(
    user_id: int = Depends(get_current_user),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Fetch content that hasn't been swiped yet.

    Returns content ordered by recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_pending(user_id, limit=limit, offset=offset, platform=platform, tags=tags)
    total = await repo.count_pending(user_id)
    has_more = (offset + limit) < total

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        next_offset=offset + limit if has_more else None,
    )


@router.get("/content/kept", response_model=PaginatedContentResponse)
async def list_kept_content(
    user_id: int = Depends(get_current_user),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Get content that was swiped Keep.

    Returns kept content ordered by swipe recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_kept(user_id, limit=limit, offset=offset, platform=platform, tags=tags)
    total = await repo.count_kept(user_id)
    has_more = (offset + limit) < total

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        next_offset=offset + limit if has_more else None,
    )


@router.get("/content/discarded", response_model=PaginatedContentResponse)
async def list_discarded_content(
    user_id: int = Depends(get_current_user),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Get content that was swiped Discard.

    Returns discarded content ordered by swipe recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_discarded(user_id, limit=limit, offset=offset, platform=platform, tags=tags)
    total = await repo.count_discarded(user_id)
    has_more = (offset + limit) < total

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        next_offset=offset + limit if has_more else None,
    )
