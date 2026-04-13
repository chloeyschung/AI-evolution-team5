"""API route handlers for content and swipe operations."""

from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import outerjoin

from src.ai.metadata_extractor import ContentMetadata
from src.ingestion.share_handler import ShareHandler

from ..data.database import get_db
from ..data.models import Content, SwipeHistory
from ..data.repository import ContentRepository, SwipeRepository, UserProfileRepository
from .schemas import (
    ContentCreate,
    ContentResponse,
    SwipeCreate,
    SwipeResponse,
    SwipeBatchRequest,
    SwipeBatchResponse,
    StatsResponse,
    ShareRequest,
    ShareResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserStatisticsResponse,
    InterestTagRequest,
    InterestTagResponse,
)
from src.data.models import ContentStatus

router = APIRouter()


@router.post("/content", status_code=201, response_model=ContentResponse)
async def create_content(
    data: ContentCreate,
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Save new content metadata."""
    metadata = ContentMetadata(
        platform=data.platform,
        content_type=data.content_type,
        url=data.url,
        title=data.title,
        author=data.author,
    )

    result = await db.execute(select(Content).where(Content.url == metadata.url))
    existing = result.scalar_one_or_none()

    if existing:
        existing.platform = metadata.platform
        existing.content_type = metadata.content_type.value
        existing.title = metadata.title
        existing.author = metadata.author
        existing.timestamp = metadata.timestamp
        await db.commit()
        await db.refresh(existing)
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
        await db.commit()
        await db.refresh(content)

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
    limit: int = Query(50, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """List all content."""
    result = await db.execute(
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
async def record_swipe(
    data: Union[SwipeCreate, SwipeBatchRequest],
    db: AsyncSession = Depends(get_db),
) -> Union[SwipeResponse, SwipeBatchResponse]:
    """Record a swipe action (single or batch)."""
    repo = SwipeRepository(db)

    if isinstance(data, SwipeBatchRequest):
        actions = [(a.content_id, a.action) for a in data.actions]
        histories = await repo.record_swipes_batch(actions)
        return SwipeBatchResponse(
            recorded=len(histories),
            results=[
                SwipeResponse(id=h.id, content_id=h.content_id, action=h.action.value)
                for h in histories
            ],
        )
    else:
        history = await repo.record_swipe(data.content_id, data.action)
        return SwipeResponse(
            id=history.id,
            content_id=history.content_id,
            action=history.action.value,
        )


@router.get("/content/pending", response_model=list[ContentResponse])
async def list_pending_content(
    limit: int = Query(50, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Fetch content that hasn't been swiped yet.

    Returns content ordered by recency (newest first).
    """
    result = await db.execute(
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
async def list_kept_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Keep.

    Returns kept content ordered by swipe recency (newest first).
    """
    repo = ContentRepository(db)
    contents = await repo.get_kept(limit=limit, offset=offset)

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
async def list_discarded_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Discard.

    Returns discarded content ordered by swipe recency (newest first).
    """
    repo = ContentRepository(db)
    contents = await repo.get_discarded(limit=limit, offset=offset)

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


@router.patch("/content/{content_id}/status", response_model=ContentResponse)
async def update_content_status(
    content_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Update content status (INBOX → ARCHIVED transition).

    Args:
        content_id: The content ID to update.
        data: Dictionary with "status" field (must be "archived").
        db: Database session.

    Returns:
        Updated Content object.

    Raises:
        404: Content not found.
        400: Invalid status transition.
    """
    repo = ContentRepository(db)
    new_status = ContentStatus(data.get("status", "archived"))

    try:
        content = await repo.update_status(content_id, new_status)
        return ContentResponse(
            id=content.id,
            platform=content.platform,
            content_type=content.content_type,
            url=content.url,
            title=content.title,
            author=content.author,
            status=content.status,
            created_at=content.created_at.isoformat(),
            updated_at=content.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_content_stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    """Get content statistics.

    Returns counts of pending, kept, and discarded content.
    """
    repo = ContentRepository(db)
    stats = await repo.get_stats()

    return StatsResponse(
        pending=stats["pending"],
        kept=stats["kept"],
        discarded=stats["discarded"],
    )


# Share handler dependency - initialized in app.py
_share_handler: ShareHandler | None = None


def _set_share_handler(handler: ShareHandler) -> None:
    """Set the share handler instance for dependency injection."""
    global _share_handler
    _share_handler = handler


def get_share_handler() -> ShareHandler:
    """Get the share handler instance."""
    if _share_handler is None:
        raise RuntimeError("ShareHandler not initialized. Configure it in app.py.")
    return _share_handler


@router.post("/share", status_code=201, response_model=ShareResponse)
async def share_content(
    data: ShareRequest,
    db: AsyncSession = Depends(get_db),
    share_handler: ShareHandler = Depends(get_share_handler),
) -> ShareResponse:
    """Process shared content from mobile share sheet.

    Automatically extracts content, generates summary, and stores it.
    """
    # Process share data
    raw_payload = {
        "content": data.content,
        "platform": data.platform,
        "metadata": data.metadata,
    }

    metadata = await share_handler.process_share(raw_payload)

    # Check if content already exists
    result = await db.execute(select(Content).where(Content.url == metadata.url))
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing content
        existing.platform = metadata.platform
        existing.content_type = metadata.content_type.value
        existing.title = metadata.title
        existing.author = metadata.author
        existing.timestamp = metadata.timestamp
        # Note: summary is not regenerated for existing content
        await db.commit()
        await db.refresh(existing)
        content = existing
    else:
        # Create new content
        content = Content(
            platform=metadata.platform,
            content_type=metadata.content_type.value,
            url=metadata.url,
            title=metadata.title,
            author=metadata.author,
            timestamp=metadata.timestamp,
            summary=getattr(metadata, "summary", None),
        )
        db.add(content)
        await db.commit()
        await db.refresh(content)

    return ShareResponse(
        id=content.id,
        platform=content.platform,
        content_type=content.content_type,
        url=content.url,
        title=content.title,
        author=content.author,
        summary=content.summary,
        created_at=content.created_at.isoformat(),
    )


# DAT-002: User Profile & Preferences endpoints


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(db: AsyncSession = Depends(get_db)) -> UserProfileResponse:
    """Get user profile.

    Auto-creates profile if it doesn't exist.
    """
    repo = UserProfileRepository(db)
    profile = await repo.get_or_create_profile()

    return UserProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update user profile."""
    repo = UserProfileRepository(db)
    profile = await repo.update_profile(
        display_name=data.display_name,
        avatar_url=data.avatar_url,
        bio=data.bio,
    )

    return UserProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)) -> UserPreferencesResponse:
    """Get user preferences.

    Auto-creates preferences with defaults if they don't exist.
    """
    repo = UserProfileRepository(db)
    preferences = await repo.get_preferences()

    return UserPreferencesResponse(
        theme=preferences.theme,
        notifications_enabled=bool(preferences.notifications_enabled),
        daily_goal=preferences.daily_goal,
        default_sort=preferences.default_sort,
    )


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    data: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Update user preferences."""
    repo = UserProfileRepository(db)
    preferences = await repo.update_preferences(
        theme=data.theme,
        notifications_enabled=data.notifications_enabled,
        daily_goal=data.daily_goal,
        default_sort=data.default_sort,
    )

    return UserPreferencesResponse(
        theme=preferences.theme,
        notifications_enabled=bool(preferences.notifications_enabled),
        daily_goal=preferences.daily_goal,
        default_sort=preferences.default_sort,
    )


@router.get("/user/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(db: AsyncSession = Depends(get_db)) -> UserStatisticsResponse:
    """Get user statistics from swipe history.

    Returns aggregated metrics including swipe counts, retention rate, and streak.
    """
    repo = UserProfileRepository(db)
    stats = await repo.get_statistics()

    return UserStatisticsResponse(
        total_swipes=stats["total_swipes"],
        total_kept=stats["total_kept"],
        total_discarded=stats["total_discarded"],
        retention_rate=stats["retention_rate"],
        streak_days=stats["streak_days"],
        first_swipe_at=stats["first_swipe_at"].isoformat() if stats["first_swipe_at"] else None,
        last_swipe_at=stats["last_swipe_at"].isoformat() if stats["last_swipe_at"] else None,
    )


@router.get("/interests", response_model=list[str])
async def get_interests(db: AsyncSession = Depends(get_db)) -> list[str]:
    """Get all user interest tags."""
    repo = UserProfileRepository(db)
    return await repo.get_interest_tags()


@router.post("/interests", status_code=201, response_model=InterestTagResponse)
async def add_interest(
    data: InterestTagRequest,
    db: AsyncSession = Depends(get_db),
) -> InterestTagResponse:
    """Add an interest tag.

    Tags are case-insensitive and unique per user.
    """
    repo = UserProfileRepository(db)
    tag = await repo.add_interest_tag(data.tag)

    return InterestTagResponse(id=tag.id, tag=tag.tag)


@router.delete("/interests/{tag}")
async def remove_interest(tag: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Remove an interest tag."""
    repo = UserProfileRepository(db)
    await repo.remove_interest_tag(tag)

    return {"message": f"Interest tag '{tag}' removed successfully"}
