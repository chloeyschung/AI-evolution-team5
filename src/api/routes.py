"""API route handlers for content and swipe operations."""

from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.metadata_extractor import ContentMetadata
from src.ingestion.share_handler import ShareHandler

from ..data.database import get_db
from ..data.models import Content
from ..data.repository import ContentRepository, SwipeRepository, UserProfileRepository
from ..data.auth_repository import AuthenticationRepository
from .schemas import (
    ContentCreate,
    ContentResponse,
    ContentDetailResponse,
    SwipeHistoryResponse,
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
    AuthStatusResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
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

    repo = ContentRepository(db)
    content = await repo.save(metadata)

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
    repo = ContentRepository(db)
    contents = await repo.get_pending(limit=limit)

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


# UX-003: Content Detail View


@router.get("/content/{content_id}", response_model=ContentDetailResponse)
async def get_content_detail(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> ContentDetailResponse:
    """Get content detail with swipe history."""
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if content is None:
        raise HTTPException(status_code=404, detail=f"Content with ID {content_id} not found")

    swipe_repo = SwipeRepository(db)
    history = await swipe_repo.get_history(content_id)
    swipe_history = None
    if history:
        latest = history[-1]
        swipe_history = SwipeHistoryResponse(
            action=latest.action.value,
            swiped_at=latest.swiped_at.isoformat(),
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
        created_at=content.created_at.isoformat(),
        updated_at=content.updated_at.isoformat() if content.updated_at else None,
    )


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

    # Save content using repository
    repo = ContentRepository(db)
    content = await repo.save(metadata)

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


# AUTH-001: Authentication endpoints


@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> AuthStatusResponse:
    """Check current authentication status.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Auth status with user info if authenticated.
    """
    # No token provided
    if not authorization or not authorization.startswith("Bearer "):
        return AuthStatusResponse(is_authenticated=False)

    # Extract token
    token = authorization[7:]  # Remove "Bearer " prefix
    auth_repo = AuthenticationRepository(db)

    # Get token from database
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        return AuthStatusResponse(is_authenticated=False)

    # Return authenticated status
    return AuthStatusResponse(
        is_authenticated=True,
        user_id=token_record.user_id,
        token_expires_at=token_record.expires_at.isoformat(),
    )


@router.post("/auth/refresh", response_model=TokenRefreshResponse)
async def refresh_auth_token(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    """Refresh access token using refresh token.

    Implements token rotation: issues new refresh token on each refresh.

    Args:
        data: Refresh token request.
        db: Database session.

    Returns:
        New access token and expiry time.

    Raises:
        401: Invalid or expired refresh token.
    """
    auth_repo = AuthenticationRepository(db)

    # Refresh token (includes token rotation)
    token_record = await auth_repo.refresh_access_token(data.refresh_token)

    if not token_record:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")

    return TokenRefreshResponse(
        access_token=token_record.access_token,
        expires_at=token_record.expires_at.isoformat(),
    )


# AUTH-002: Google OAuth endpoint


@router.post("/auth/google", status_code=200, response_model=GoogleLoginResponse)
async def google_login(
    data: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> GoogleLoginResponse:
    """Authenticate with Google and get access tokens.

    Handles:
    - New user registration (auto-create account)
    - Existing user login (issue new tokens)
    - 30-day re-registration block enforcement

    Args:
        data: Google login request with ID token and user info.
        db: Database session.

    Returns:
        Access tokens and user info.

    Raises:
        401: Invalid Google ID token.
        403: Account within 30-day re-registration block.
    """
    from src.auth.google_oauth import verify_google_id_token, extract_user_info_from_token, GoogleTokenVerificationError
    from src.data.repository import UserProfileRepository, AccountDeletionRepository

    # Verify Google ID token
    try:
        token_info = await verify_google_id_token(data.google_id_token)
    except GoogleTokenVerificationError as e:
        raise HTTPException(status_code=401, detail=f"invalid_google_token: {str(e)}")

    # Extract user info
    user_info = extract_user_info_from_token(token_info)
    email = data.google_user_info.email
    google_sub = data.google_user_info.id

    # Check for 30-day re-registration block
    deletion_repo = AccountDeletionRepository(db)
    is_blocked, block_expires_at = await deletion_repo.is_account_blocked(
        email=email, google_sub=google_sub
    )

    if is_blocked:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_restriction",
                "message": "Account recently deleted. Please wait 30 days before re-registering.",
                "available_at": block_expires_at.isoformat(),
            },
        )

    # Check if user already exists
    user_repo = UserProfileRepository(db)
    existing_user = await user_repo.get_user_by_email(email)

    if not existing_user:
        # Check by google_sub as fallback
        existing_user = await user_repo.get_user_by_google_sub(google_sub)

    auth_repo = AuthenticationRepository(db)
    is_new_user = False

    if existing_user:
        # Existing user: update last login
        await user_repo.update_last_login(existing_user.id)
    else:
        # New user: create account
        existing_user = await user_repo.create_user(
            email=email,
            google_sub=google_sub,
            display_name=data.google_user_info.name,
            avatar_url=data.google_user_info.picture,
        )
        is_new_user = True

    # Create authentication tokens
    token_record = await auth_repo.create_tokens(existing_user.id)

    return GoogleLoginResponse(
        access_token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        expires_at=token_record.expires_at.isoformat(),
        user={
            "id": existing_user.id,
            "email": existing_user.email,
            "display_name": existing_user.display_name,
            "avatar_url": existing_user.avatar_url,
        },
        is_new_user=is_new_user,
    )
