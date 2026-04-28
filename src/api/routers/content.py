"""Content domain router — /content/* CRUD, /stats, /platforms, /search, /share."""

import logging
import os
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi import Request as FastAPIRequest
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants import ErrorCode
from ...data.database import AsyncSessionLocal, get_db
from ...data.models import ContentStatus
from ...data.repository import (
    ContentRepository,
    ContentTagRepository,
    SwipeRepository,
)
from ...ingestion.share_handler import ShareHandler
from ...middleware.rate_limiter import limiter
from ...services import ContentService
from ...utils.cursor_pagination import (
    CursorTokenError,
    make_timestamp_cursor,
    parse_timestamp_cursor,
)
from ...utils.datetime_utils import serialize_datetime
from ..dependencies import get_current_user
from ..schemas import (
    ContentCreate,
    ContentDetailResponse,
    ContentResponse,
    ContentStatusUpdate,
    ContentTagsResponse,
    DeleteContentResponse,
    DeletedContentResponse,
    PaginatedContentResponse,
    PlatformCount,
    ShareRequest,
    ShareResponse,
    StatsResponse,
    SwipeHistoryResponse,
    TrendFeedItem,
    TrendFeedResponse,
)

router = APIRouter()


def _invalid_cursor_http_exception() -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": "invalid_cursor", "message": "Malformed cursor token."},
    )


@router.post("/content", status_code=201, response_model=ContentResponse)
async def create_content(
    data: ContentCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Save new content metadata.

    TODO #3 (2026-04-14): Added user_id parameter to associate content with authenticated user.
    """
    service = ContentService(db)
    content = await service.create_content(
        platform=data.platform,
        content_type=data.content_type,
        url=data.url,
        title=data.title,
        author=data.author,
        user_id=user_id,
    )

    return ContentResponse.from_content(content)


@router.get("/content", response_model=PaginatedContentResponse)
async def list_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(None),
    status: str | None = Query(None, pattern="^(inbox|archived)$"),
    platform: str | None = Query(None),
    sort: str = Query("recency", pattern="^(recency|platform|title|status)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """List all content for the authenticated user.

    Returns a pagination wrapper with items, has_more, total, and next_offset (DAT-001 FR-6).
    Supports filtering by status (inbox/archived) and platform.
    has_more is True when len(items) == limit, indicating there may be more pages.
    next_offset is offset + len(items) when has_more is True, else None.
    """
    repo = ContentRepository(db)
    status_filter: ContentStatus | None = None
    if status == "inbox":
        status_filter = ContentStatus.INBOX
    elif status == "archived":
        status_filter = ContentStatus.ARCHIVED

    is_cursor_mode = cursor is not None and sort == "recency"
    if is_cursor_mode:
        try:
            cursor_created_at, cursor_id = parse_timestamp_cursor(
                cursor,
                expected_scope="content:list",
            )
        except CursorTokenError as exc:
            raise _invalid_cursor_http_exception() from exc

        contents = await repo.get_all_ordered(
            user_id=user_id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            status=status_filter,
            platform=platform,
            sort=sort,
            order=order,
        )
    else:
        contents = await repo.get_all_ordered(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status_filter,
            platform=platform,
            sort=sort,
            order=order,
        )

    total = await repo.count_all(user_id=user_id, status=status_filter, platform=platform)
    has_more = len(contents) == limit
    next_cursor = None
    next_offset = offset + len(contents) if has_more else None
    if has_more and contents:
        last_item = contents[-1]
        next_cursor = make_timestamp_cursor(
            scope="content:list",
            sort_ts=last_item.created_at,
            tie_breaker_id=last_item.id,
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


# ADV-001: Personalized Trend Feed endpoints


@router.get("/content/trend-feed", response_model=TrendFeedResponse)
async def get_trend_feed(
    limit: int = Query(20, gt=0, le=50, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    time_range: str = Query(
        "all",
        pattern="^(week|month|all)$",
        description="Time range filter: week, month, or all",
    ),
    min_score: float = Query(0.1, ge=0, le=1, description="Minimum relevance score threshold"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrendFeedResponse:
    """Get personalized trend feed for authenticated user.

    Returns kept content ranked by relevance score based on:
    - User's interest tags
    - Content tag similarity with preferred tags
    - Recency (when content was kept)
    - Engagement (keep ratio for same tags)

    Args:
        limit: Maximum items to return (1-50)
        offset: Pagination offset
        time_range: Filter by week, month, or all time
        min_score: Minimum relevance score threshold (0-1)
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Trend feed response with ranked items and metadata

    Raises:
        401: Not authenticated
    """
    from src.ai.trend_analyzer import TrendAnalyzer

    # Get trend feed
    analyzer = TrendAnalyzer(db)
    items, total = await analyzer.get_trend_feed(
        user_id=user_id,
        limit=limit,
        offset=offset,
        time_range=time_range,
        min_score=min_score,
    )

    # Build response
    response_items = [
        TrendFeedItem(
            content=ContentResponse.from_content(item.content),
            relevance_score=item.relevance_score,
            matched_interests=item.matched_interests,
            top_tags=item.top_tags,
        )
        for item in items
    ]

    return TrendFeedResponse(
        items=response_items,
        total=total,
        has_more=offset + limit < total,
    )


@router.get("/content/trash", response_model=PaginatedContentResponse)
async def list_trash(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> PaginatedContentResponse:
    """List soft-deleted content for the authenticated user (trash can view)."""
    content_repo = ContentRepository(db)
    items = await content_repo.get_trash(user_id, limit=limit, offset=offset)
    total = len(items)
    has_more = len(items) == limit
    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in items],
        has_more=has_more,
        total=total,
        pagination_mode="offset",
        next_offset=(offset + len(items)) if has_more else None,
        next_cursor=None,
    )


@router.delete("/content/trash", response_model=DeleteContentResponse)
async def clear_trash(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> DeleteContentResponse:
    """Permanently delete all soft-deleted content for the authenticated user."""
    content_repo = ContentRepository(db)
    deleted_count = await content_repo.clear_trash(user_id)
    return DeleteContentResponse(message=f"Permanently deleted {deleted_count} item(s) from trash.")


# UX-003: Content Detail View


@router.get("/content/{content_id}", response_model=ContentDetailResponse)
async def get_content_detail(
    content_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentDetailResponse:
    """Get content detail with swipe history."""
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if content is None or content.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )

    swipe_repo = SwipeRepository(db)
    history = await swipe_repo.get_history(content_id)
    swipe_history = None
    if history:
        latest = history[-1]
        swipe_history = SwipeHistoryResponse(
            action=latest.action.value,
            swiped_at=serialize_datetime(latest.swiped_at),
        )

    return ContentDetailResponse(
        id=content.id,
        platform=content.platform,
        content_type=content.content_type,
        url=content.url,
        title=content.title,
        author=content.author,
        summary=content.summary,
        status=content.status,
        swipe_history=swipe_history,
        created_at=serialize_datetime(content.created_at),
        updated_at=serialize_datetime(content.updated_at),
    )


@router.patch("/content/{content_id}/status", response_model=ContentResponse)
async def update_content_status(
    content_id: int,
    data: ContentStatusUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Update content status (INBOX → ARCHIVED transition).

    Args:
        content_id: The content ID to update.
        data: ContentStatusUpdate with "status" field.
        user_id: Authenticated user ID.
        db: Database session.

    Returns:
        Updated Content object.

    Raises:
        404: Content not found.
        400: Invalid status transition.
    """
    repo = ContentRepository(db)

    try:
        content = await repo.update_status(content_id, data.status, user_id=user_id)
        return ContentResponse.from_content(content)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_status_transition", "message": "Invalid status transition requested."},
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        ) from e


# AI-003: Content Categorization endpoints


@router.get("/content/{content_id}/tags", response_model=ContentTagsResponse)
async def get_content_tags(
    content_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentTagsResponse:
    """Get AI-generated tags for content.

    Args:
        content_id: The content ID.
        user_id: Authenticated user ID.
        db: Database session.

    Returns:
        Content tags response.

    Raises:
        404: Content not found.
    """
    # Check if content exists and belongs to user
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if not content or content.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )

    # Get tags
    tag_repo = ContentTagRepository(db)
    tags = await tag_repo.get_tags(content_id)

    return ContentTagsResponse(content_id=content_id, tags=tags)


@router.post("/content/{content_id}/categorize", response_model=ContentTagsResponse)
async def categorize_content(
    content_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentTagsResponse:
    """Trigger AI categorization for content.

    Generates 1-3 category tags using LLM.

    Args:
        content_id: The content ID to categorize.
        user_id: Authenticated user ID.
        db: Database session.

    Returns:
        Content tags response.

    Raises:
        404: Content not found.
    """
    from src.ai.categorizer import Categorizer
    from src.ai.summarizer import Summarizer

    # Check if content exists and belongs to user
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if not content or content.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )

    # Initialize categorizer
    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not summarizer_api_key:
        raise HTTPException(
            status_code=500,
            detail={"error": "anthropic_api_key_not_configured", "message": "Anthropic API key is not configured."},
        )

    summarizer = Summarizer(api_key=summarizer_api_key)
    categorizer = Categorizer(summarizer)

    # Generate tags
    tags = await categorizer.generate_tags(title=content.title or "", summary=content.summary)

    # Save tags to database
    tag_repo = ContentTagRepository(db)
    await tag_repo.add_tags(content_id, tags)

    return ContentTagsResponse(content_id=content_id, tags=tags)


# DAT-003: Soft Delete Content endpoint


@router.delete("/content/{content_id}", response_model=DeletedContentResponse)
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> DeletedContentResponse:
    """Soft-delete content (sets is_deleted flag, does not remove row).

    Content can be restored within 30 days via the restore endpoint.

    Args:
        content_id: The content ID to soft-delete.
        db: Database session.
        user_id: Authenticated user ID.

    Returns:
        Soft-delete confirmation with recoverable_until timestamp.

    Raises:
        404: Content not found or not owned by user.
    """
    content_repo = ContentRepository(db)
    content = await content_repo.soft_delete_content(content_id, user_id)

    if content is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )

    deleted_at = content.deleted_at
    recoverable_until = deleted_at + timedelta(days=30)

    return DeletedContentResponse(
        id=content.id,
        is_deleted=content.is_deleted,
        deleted_at=deleted_at,
        recoverable_until=recoverable_until,
    )


@router.delete("/content/{content_id}/purge", response_model=DeleteContentResponse)
async def purge_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> DeleteContentResponse:
    """Permanently delete one content row from trash.

    This is intended for explicit hard-delete actions in Trash UI.
    """
    content_repo = ContentRepository(db)
    deleted = await content_repo.delete_content(content_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )
    return DeleteContentResponse(message="Content permanently deleted.")


@router.post("/content/{content_id}/restore", response_model=ContentResponse)
async def restore_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ContentResponse:
    """Restore soft-deleted content within the 30-day recovery window (DAT-003).

    Args:
        content_id: The content ID to restore.
        db: Database session.
        user_id: Authenticated user ID.

    Returns:
        Restored Content object.

    Raises:
        404: Content not found or not deleted.
        410: Recovery window has expired.
    """
    content_repo = ContentRepository(db)

    try:
        content = await content_repo.restore_content(content_id, user_id)
        return ContentResponse.from_content(content)
    except ValueError:
        raise HTTPException(
            status_code=410,
            detail={"error": "recovery_window_expired", "message": "The 30-day recovery window has expired."},
        )
    except RuntimeError:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.CONTENT_NOT_FOUND, "message": "Content not found."},
        )


@router.get("/stats", response_model=StatsResponse)
async def get_content_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """Get content statistics for the authenticated user.

    Returns counts of pending, kept, and discarded content.
    """
    repo = ContentRepository(db)
    stats = await repo.get_stats(user_id=user_id)

    return StatsResponse(
        pending=stats["pending"],
        kept=stats["kept"],
        discarded=stats["discarded"],
    )


# UX-004: Get platforms endpoint


@router.get("/platforms", response_model=list[PlatformCount])
async def list_platforms(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlatformCount]:
    """Get list of platforms user has saved content from.

    Returns platforms with content counts, sorted by count descending.
    """
    repo = ContentRepository(db)
    platform_counts = await repo.get_platform_counts(user_id=user_id)

    return [PlatformCount(platform=p, count=c) for p, c in platform_counts]


# UX-005: Search endpoint


@router.get("/search", response_model=PaginatedContentResponse)
async def search_content(
    user_id: int = Depends(get_current_user),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedContentResponse:
    """Search content by title, author, or tags.

    Real-time search across all content (INBOX + ARCHIVED).
    Case-insensitive search.

    Args:
        q: Search query string (minimum 1 character).
        limit: Maximum number of results.
        offset: Pagination offset.
        db: Database session.

    Returns:
        Paginated response with matching content, sorted by recency.
    """
    repo = ContentRepository(db)
    is_cursor_mode = cursor is not None
    cursor_context = {"q": q}
    if is_cursor_mode:
        try:
            cursor_created_at, cursor_id = parse_timestamp_cursor(
                cursor,
                expected_scope="content:search",
                expected_context=cursor_context,
            )
        except CursorTokenError as exc:
            raise _invalid_cursor_http_exception() from exc

        results = await repo.search_content(
            user_id,
            q,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
    else:
        results = await repo.search_content(user_id, q, limit=limit, offset=offset)

    total = await repo.count_search(user_id, q)
    has_more = len(results) == limit if is_cursor_mode else (offset + limit) < total
    next_cursor = None
    next_offset = offset + limit if has_more else None
    if has_more and results:
        last_item = results[-1]
        next_cursor = make_timestamp_cursor(
            scope="content:search",
            sort_ts=last_item.created_at,
            tie_breaker_id=last_item.id,
            context=cursor_context,
        )
    if is_cursor_mode:
        next_offset = None

    return PaginatedContentResponse(
        items=[ContentResponse.from_content(c) for c in results],
        has_more=has_more,
        total=total,
        pagination_mode="cursor" if is_cursor_mode else "offset",
        next_offset=next_offset,
        next_cursor=next_cursor,
    )


# Share handler dependency - initialized in app.py (Task #11: DI pattern)
def get_share_handler(request: FastAPIRequest) -> ShareHandler:
    """Get the share handler instance from app.state."""

    share_handler = request.app.state.share_handler
    if share_handler is None:
        raise RuntimeError("ShareHandler not initialized. Configure it in app.py.")
    return share_handler


async def _background_summarize(
    content_id: int,
    user_id: int,
    url: str,
    content_extractor,
    summarizer,
) -> None:
    """Fetch page text and summarize it, then persist the result — runs after response is sent."""
    try:
        _, text_content = await content_extractor.fetch_html_and_text(url)
        if not text_content:
            return
        summary = await summarizer.summarize(text_content)
        async with AsyncSessionLocal() as db:
            repo = ContentRepository(db)
            await repo.update_summary(content_id, user_id, summary)
    except Exception as exc:
        logging.warning("Background summarization failed for content %s: %s", content_id, exc)


@router.post("/share", status_code=201, response_model=ShareResponse)
@limiter.limit("120/minute")  # Rate limit tuned for extension burst saves
async def share_content(
    request: Request,
    data: ShareRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    share_handler: ShareHandler = Depends(get_share_handler),
) -> ShareResponse:
    """Process shared content from mobile share sheet.

    Saves content immediately and runs LLM summarization in the background so
    the response is returned within ~1 s regardless of Anthropic API latency.

    TODO #3 (2026-04-14): Added user_id parameter to associate content with authenticated user.
    """
    options = dict(data.options or {})
    auto_summarize = options.pop("auto_summarize", True)

    # Disable inline summarization — we'll schedule it as a background task
    raw_payload = {
        "content": data.content,
        "platform": data.platform,
        "metadata": data.metadata,
        "options": {**options, "auto_summarize": False},
    }

    metadata = await share_handler.process_share(raw_payload)

    # Save content immediately (no summary yet)
    repo = ContentRepository(db)
    content = await repo.save(metadata, user_id=user_id)

    # Schedule summarization to run after the response is sent
    if auto_summarize and share_handler._summarizer and data.content:
        background_tasks.add_task(
            _background_summarize,
            content.id,
            user_id,
            data.content,
            share_handler._content_extractor,
            share_handler._summarizer,
        )

    return ShareResponse(
        id=content.id,
        platform=content.platform,
        content_type=content.content_type,
        url=content.url,
        title=content.title,
        author=content.author,
        summary=content.summary,
        created_at=serialize_datetime(content.created_at),
    )
