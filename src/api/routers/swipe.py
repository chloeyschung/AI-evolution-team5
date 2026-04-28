"""Swipe domain router — /swipe/* and /content/pending, /content/kept, /content/discarded."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.repository import ContentRepository
from ...services import SwipeService
from ...utils.cursor_pagination import (
    CursorTokenError,
    make_timestamp_cursor,
    parse_timestamp_cursor,
)
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


def _invalid_cursor_http_exception() -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": "invalid_cursor", "message": "Malformed cursor token."},
    )


def _cursor_filter_context(platform: str | None, tags: list[str] | None) -> dict[str, str | list[str]]:
    return {
        "platform": platform or "",
        "tags": sorted(tags or []),
    }


@router.post("/swipe/batch", status_code=201, response_model=SwipeBatchResponse)
async def record_swipe_batch(
    data: SwipeBatchRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SwipeBatchResponse:
    """Record a batch of swipe actions."""
    service = SwipeService(db)
    actions = [(a.content_id, a.action) for a in data.actions]
    try:
        result = await service.record_swipes_batch(actions, user_id=user_id)
    except ValueError as exc:
        if str(exc) == "content_not_found":
            raise HTTPException(
                status_code=404,
                detail={"error": "content_not_found", "message": "Content not found."},
            ) from exc
        raise
    return SwipeBatchResponse(
        recorded=result.recorded,
        results=[SwipeResponse(id=r.id, content_id=r.content_id, action=r.action.value) for r in result.results],
    )


@router.post("/swipe", status_code=201, response_model=SwipeResponse)
async def record_swipe(
    data: SwipeCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SwipeResponse:
    """Record a single swipe action."""
    service = SwipeService(db)
    try:
        result = await service.record_swipe(data.content_id, data.action, user_id=user_id)
    except ValueError as exc:
        if str(exc) == "content_not_found":
            raise HTTPException(
                status_code=404,
                detail={"error": "content_not_found", "message": "Content not found."},
            ) from exc
        raise
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
    cursor: str | None = Query(None),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Fetch content that hasn't been swiped yet.

    Returns content ordered by recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    is_cursor_mode = cursor is not None
    cursor_context = _cursor_filter_context(platform, tags)
    if is_cursor_mode:
        try:
            cursor_created_at, cursor_id = parse_timestamp_cursor(
                cursor,
                expected_scope="content:pending",
                expected_context=cursor_context,
            )
        except CursorTokenError as exc:
            raise _invalid_cursor_http_exception() from exc
        contents = await repo.get_pending(
            user_id,
            limit=limit,
            platform=platform,
            tags=tags,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
    else:
        contents = await repo.get_pending(user_id, limit=limit, offset=offset, platform=platform, tags=tags)

    total = await repo.count_pending(user_id)
    has_more = len(contents) == limit if is_cursor_mode else (offset + limit) < total
    next_cursor = None
    next_offset = offset + limit if has_more else None
    if has_more and contents:
        last_item = contents[-1]
        next_cursor = make_timestamp_cursor(
            scope="content:pending",
            sort_ts=last_item.created_at,
            tie_breaker_id=last_item.id,
            context=cursor_context,
        )
    if is_cursor_mode:
        next_offset = None

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        pagination_mode="cursor" if is_cursor_mode else "offset",
        next_offset=next_offset,
        next_cursor=next_cursor,
    )


@router.get("/content/kept", response_model=PaginatedContentResponse)
async def list_kept_content(
    user_id: int = Depends(get_current_user),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(None),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Get content that was swiped Keep.

    Returns kept content ordered by swipe recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    is_cursor_mode = cursor is not None
    cursor_context = _cursor_filter_context(platform, tags)
    if is_cursor_mode:
        try:
            cursor_swiped_at, cursor_content_id = parse_timestamp_cursor(
                cursor,
                expected_scope="content:kept",
                expected_context=cursor_context,
            )
        except CursorTokenError as exc:
            raise _invalid_cursor_http_exception() from exc
        contents = await repo.get_kept(
            user_id,
            limit=limit,
            platform=platform,
            tags=tags,
            cursor_swiped_at=cursor_swiped_at,
            cursor_content_id=cursor_content_id,
        )
    else:
        contents = await repo.get_kept(user_id, limit=limit, offset=offset, platform=platform, tags=tags)

    total = await repo.count_kept(user_id)
    has_more = len(contents) == limit if is_cursor_mode else (offset + limit) < total
    next_cursor = None
    next_offset = offset + limit if has_more else None
    if has_more and contents:
        last_item = contents[-1]
        latest_swipe_ts = getattr(last_item, "_cursor_swiped_at", None)
        if latest_swipe_ts is not None:
            next_cursor = make_timestamp_cursor(
                scope="content:kept",
                sort_ts=latest_swipe_ts,
                tie_breaker_id=last_item.id,
                context=cursor_context,
            )
    if is_cursor_mode:
        next_offset = None

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        pagination_mode="cursor" if is_cursor_mode else "offset",
        next_offset=next_offset,
        next_cursor=next_cursor,
    )


@router.get("/content/discarded", response_model=PaginatedContentResponse)
async def list_discarded_content(
    user_id: int = Depends(get_current_user),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(None),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Get content that was swiped Discard.

    Returns discarded content ordered by swipe recency (newest first) with pagination envelope.
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    is_cursor_mode = cursor is not None
    cursor_context = _cursor_filter_context(platform, tags)
    if is_cursor_mode:
        try:
            cursor_swiped_at, cursor_content_id = parse_timestamp_cursor(
                cursor,
                expected_scope="content:discarded",
                expected_context=cursor_context,
            )
        except CursorTokenError as exc:
            raise _invalid_cursor_http_exception() from exc
        contents = await repo.get_discarded(
            user_id,
            limit=limit,
            platform=platform,
            tags=tags,
            cursor_swiped_at=cursor_swiped_at,
            cursor_content_id=cursor_content_id,
        )
    else:
        contents = await repo.get_discarded(user_id, limit=limit, offset=offset, platform=platform, tags=tags)

    total = await repo.count_discarded(user_id)
    has_more = len(contents) == limit if is_cursor_mode else (offset + limit) < total
    next_cursor = None
    next_offset = offset + limit if has_more else None
    if has_more and contents:
        last_item = contents[-1]
        latest_swipe_ts = getattr(last_item, "_cursor_swiped_at", None)
        if latest_swipe_ts is not None:
            next_cursor = make_timestamp_cursor(
                scope="content:discarded",
                sort_ts=latest_swipe_ts,
                tie_breaker_id=last_item.id,
                context=cursor_context,
            )
    if is_cursor_mode:
        next_offset = None

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in contents],
        has_more=has_more,
        total=total,
        pagination_mode="cursor" if is_cursor_mode else "offset",
        next_offset=next_offset,
        next_cursor=next_cursor,
    )
