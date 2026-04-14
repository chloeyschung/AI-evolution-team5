"""API route handlers for content and swipe operations."""

import asyncio
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from ..middleware.rate_limiter import limiter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

# Track background tasks for proper lifecycle management
_background_tasks: set[asyncio.Task] = set()

from src.ai.metadata_extractor import ContentMetadata
from src.ingestion.share_handler import ShareHandler

from ..data.database import get_db
from ..data.models import Content
from ..data.repository import (
    ContentRepository,
    SwipeRepository,
    UserProfileRepository,
    ContentTagRepository,
)
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
    DeleteContentResponse,
    PlatformCount,
    ContentTagsResponse,
    AuthStatusResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
    LogoutResponse,
    AccountDeleteRequest,
    AccountDeleteResponse,
    YouTubePlaylistResponse,
    YouTubeConnectionStatus,
    YouTubeSyncConfigCreate,
    YouTubeSyncConfigResponse,
    YouTubeSyncConfigUpdate,
    YouTubeSyncLogResponse,
    YouTubeDisconnectResponse,
    LinkedInConnectionStatus,
    LinkedInSyncConfigCreate,
    LinkedInSyncConfigResponse,
    LinkedInSyncLogResponse,
    LinkedInDisconnectResponse,
    LinkedInImportRequest,
    TrendFeedResponse,
    TrendFeedItem,
    AchievementsListResponse,
    AchievementsStatsResponse,
    CheckAchievementsResponse,
    ReminderPreferencesResponse,
    ReminderPreferencesUpdate,
    ReminderSuggestionResponse,
    ReminderRespondRequest,
    ReminderRespondResponse,
)
from src.data.models import ContentStatus, Provider, IntegrationTokens, IntegrationSyncConfig, IntegrationSyncLog

router = APIRouter()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None),
) -> int:
    """Get current user ID from Bearer token.

    Args:
        db: Database session
        authorization: Authorization header with Bearer token

    Returns:
        User ID

    Raises:
        401: Invalid or missing token
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]  # Remove "Bearer " prefix
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    return token_record.user_id


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

    return ContentResponse.from_content(content)


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

    return [ContentResponse.from_content(c) for c in contents]


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
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Fetch content that hasn't been swiped yet.

    Returns content ordered by recency (newest first).
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_pending(limit=limit, platform=platform, tags=tags)

    return [ContentResponse.from_content(c) for c in contents]


@router.get("/content/kept", response_model=list[ContentResponse])
async def list_kept_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Keep.

    Returns kept content ordered by swipe recency (newest first).
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_kept(limit=limit, offset=offset, platform=platform, tags=tags)

    return [ContentResponse.from_content(c) for c in contents]


@router.get("/content/discarded", response_model=list[ContentResponse])
async def list_discarded_content(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None),  # UX-004: Filter by platform
    tags: list[str] | None = Query(None),  # F-014: Filter by AI-generated tags
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Get content that was swiped Discard.

    Returns discarded content ordered by swipe recency (newest first).
    Optionally filter by platform and AI-generated tags.
    """
    repo = ContentRepository(db)
    contents = await repo.get_discarded(limit=limit, offset=offset, platform=platform, tags=tags)

    return [ContentResponse.from_content(c) for c in contents]


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
        return ContentResponse.from_content(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


# AI-003: Content Categorization endpoints


@router.get("/content/{content_id}/tags", response_model=ContentTagsResponse)
async def get_content_tags(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> ContentTagsResponse:
    """Get AI-generated tags for content.

    Args:
        content_id: The content ID.
        db: Database session.

    Returns:
        Content tags response.

    Raises:
        404: Content not found.
    """
    # Check if content exists
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="content_not_found")

    # Get tags
    tag_repo = ContentTagRepository(db)
    tags = await tag_repo.get_tags(content_id)

    return ContentTagsResponse(content_id=content_id, tags=tags)


@router.post("/content/{content_id}/categorize", response_model=ContentTagsResponse)
async def categorize_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> ContentTagsResponse:
    """Trigger AI categorization for content.

    Generates 1-3 category tags using LLM.

    Args:
        content_id: The content ID to categorize.
        db: Database session.

    Returns:
        Content tags response.

    Raises:
        404: Content not found.
    """
    from src.ai.categorizer import Categorizer

    # Check if content exists and get title/summary
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="content_not_found")

    # Initialize categorizer
    import os
    from src.ai.summarizer import Summarizer

    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not summarizer_api_key:
        raise HTTPException(
            status_code=500,
            detail="anthropic_api_key_not_configured"
        )

    summarizer = Summarizer(api_key=summarizer_api_key)
    categorizer = Categorizer(summarizer)

    # Generate tags
    tags = await categorizer.generate_tags(
        title=content.title or "",
        summary=content.summary
    )

    # Save tags to database
    tag_repo = ContentTagRepository(db)
    await tag_repo.add_tags(content_id, tags)

    return ContentTagsResponse(content_id=content_id, tags=tags)


# UX-006: Delete Content endpoint


@router.delete("/content/{content_id}", response_model=DeleteContentResponse)
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> DeleteContentResponse:
    """Permanently delete content and associated swipe history.

    This action is irreversible.

    Args:
        content_id: The content ID to delete.
        db: Database session.

    Returns:
        Deletion confirmation.

    Raises:
        404: Content not found.
    """
    from sqlalchemy import delete

    # Check if content exists
    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="content_not_found")

    from ..data.models import ContentTag

    # Delete associated records first (foreign key constraints)
    await db.execute(delete(ContentTag).where(ContentTag.content_id == content_id))
    await db.execute(delete(SwipeHistory).where(SwipeHistory.content_id == content_id))

    # Delete content
    await db.execute(delete(Content).where(Content.id == content_id))

    await db.commit()

    return DeleteContentResponse(message="Content deleted successfully")


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


# UX-004: Get platforms endpoint


@router.get("/platforms", response_model=list[PlatformCount])
async def list_platforms(db: AsyncSession = Depends(get_db)) -> list[PlatformCount]:
    """Get list of platforms user has saved content from.

    Returns platforms with content counts, sorted by count descending.
    """
    repo = ContentRepository(db)
    platform_counts = await repo.get_platform_counts()

    return [PlatformCount(platform=p, count=c) for p, c in platform_counts]


# UX-005: Search endpoint


@router.get("/search", response_model=list[ContentResponse])
async def search_content(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ContentResponse]:
    """Search content by title, author, or tags.

    Real-time search across all content (INBOX + ARCHIVED).
    Case-insensitive search.

    Args:
        q: Search query string (minimum 1 character).
        limit: Maximum number of results.
        offset: Pagination offset.
        db: Database session.

    Returns:
        List of matching content, sorted by recency.
    """
    repo = ContentRepository(db)
    results = await repo.search_content(q, limit=limit, offset=offset)

    return [ContentResponse.from_content(c) for c in results]


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
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
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


# AUTH-003: Logout endpoint


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> LogoutResponse:
    """End current session and revoke tokens.

    Local data is retained on the client and will sync on re-login.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Logout confirmation.

    Raises:
        401: Invalid or missing token.
    """
    # Validate token and get user_id
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]  # Remove "Bearer " prefix
    auth_repo = AuthenticationRepository(db)

    token_record = await auth_repo.get_token_by_access_token(token)
    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    # Revoke tokens
    await auth_repo.revoke_token_by_user_id(token_record.user_id)

    return LogoutResponse(message="Logged out successfully")


# AUTH-004: Account Delete endpoint


@router.post("/auth/account/delete", response_model=AccountDeleteResponse)
async def delete_account(
    data: AccountDeleteRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> AccountDeleteResponse:
    """Permanently delete user account and all data.

    Two-step confirmation required:
    1. First request with confirm=true returns confirmation_token
    2. Second request with confirmation_token proceeds with deletion

    All data is permanently deleted:
    - User profile
    - Authentication tokens
    - All content (saved URLs, summaries)
    - Swipe history
    - User preferences
    - Interest tags

    30-day re-registration block is enforced.

    Args:
        data: Account deletion request with confirmation.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Deletion confirmation with block expiry date.

    Raises:
        400: Missing confirmation or invalid confirmation token.
        401: Invalid or missing token.
    """
    from datetime import timedelta
    from secrets import token_urlsafe

    from sqlalchemy import delete

    from ..data.models import (
        AccountDeletion,
        AuthenticationToken,
        Content,
        InterestTag,
        SwipeHistory,
        UserPreferences,
        UserProfile,
        utc_now,
    )
    from src.data.repository import UserProfileRepository
    from src.data.repository import AccountDeletionRepository

    # Validate token and get user_id
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]  # Remove "Bearer " prefix
    auth_repo = AuthenticationRepository(db)

    token_record = await auth_repo.get_token_by_access_token(token)
    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get user profile
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    # Two-step confirmation logic
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "confirmation_required",
                "message": "Two-step confirmation required. Please confirm deletion.",
            },
        )

    # Step 1: Generate confirmation token (if no token provided)
    if not data.confirmation_token:
        # Return a confirmation token for step 2
        confirmation_token = token_urlsafe(32)
        # Store token in session (simplified: return it for client to send back)
        return AccountDeleteResponse(
            message="Confirmation token generated. Please confirm to proceed with deletion.",
            block_expires_at=confirmation_token,  # Reuse field for token
        )

    # Step 2: Confirm and delete
    now = utc_now()
    block_expires_at = now + timedelta(days=30)

    # 1. Revoke tokens (already done by getting token, but ensure)
    await auth_repo.revoke_token_by_user_id(user_id)

    # 2. Record account deletion (30-day block)
    deletion_repo = AccountDeletionRepository(db)
    await deletion_repo.record_account_deletion(
        email=user.email,  # type: ignore
        google_sub=user.google_sub,  # type: ignore
        block_days=30,
    )

    # 3. Delete all user data (order matters for foreign keys)
    # Note: Content and SwipeHistory don't have user_id (single-user MVP design)
    await db.execute(delete(UserPreferences).where(UserPreferences.user_id == user_id))
    await db.execute(delete(InterestTag).where(InterestTag.user_id == user_id))
    await db.execute(delete(SwipeHistory).where(SwipeHistory.id.isnot(None)))  # All swipes (single-user system)
    await db.execute(delete(Content).where(Content.id.isnot(None)))  # All content (single-user system)
    await db.execute(delete(AuthenticationToken).where(AuthenticationToken.user_id == user_id))
    await db.execute(delete(UserProfile).where(UserProfile.id == user_id))

    await db.commit()

    return AccountDeleteResponse(
        message="Account deleted successfully",
        block_expires_at=block_expires_at.isoformat(),
    )


# INT-001: YouTube Integration endpoints


@router.get("/integrations/youtube/status", response_model=YouTubeConnectionStatus)
async def get_youtube_connection_status(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> YouTubeConnectionStatus:
    """Check YouTube connection status.

    Args:
        user_id: User ID (from auth).
        db: Database session.

    Returns:
        Connection status with last sync time.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    repo = IntegrationRepository(db)
    tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not tokens:
        return YouTubeConnectionStatus(is_connected=False)

    # Get last sync time
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)
    last_sync_at = None
    for config in configs:
        # Check database for last_sync_at
        result = await db.execute(
            select(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
                IntegrationSyncConfig.resource_id == config.playlist_id,
            )
        )
        db_config = result.scalar_one_or_none()
        if db_config and db_config.last_sync_at:
            if last_sync_at is None or db_config.last_sync_at > last_sync_at:
                last_sync_at = db_config.last_sync_at

    return YouTubeConnectionStatus(
        is_connected=True,
        last_sync_at=last_sync_at.isoformat() if last_sync_at else None,
    )


@router.get("/integrations/youtube/playlists", response_model=list[YouTubePlaylistResponse])
async def list_youtube_playlists(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> list[YouTubePlaylistResponse]:
    """List user's YouTube playlists.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        List of YouTube playlists.

    Raises:
        401: Not connected to YouTube.
    """
    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeClient, YouTubeAuthError

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get YouTube tokens
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail="not_connected_to_youtube")

    # Create YouTube client and fetch playlists
    client = YouTubeClient(
        access_token=youtube_tokens.access_token,
        refresh_token=youtube_tokens.refresh_token,
        token_expires_at=youtube_tokens.expires_at,
    )

    try:
        playlists = await client.get_playlists()
    except YouTubeAuthError as e:
        # Token expired, delete it
        await repo.delete_tokens(user_id, Provider.YOUTUBE.value)
        raise HTTPException(status_code=401, detail="youtube_auth_expired")

    return [
        YouTubePlaylistResponse(
            playlist_id=p.playlist_id,
            title=p.title,
            description=p.description,
            thumbnail_url=p.thumbnail_url,
            video_count=p.video_count,
            is_watch_later=p.is_watch_later,
        )
        for p in playlists
    ]


@router.post("/integrations/youtube/configs", status_code=201, response_model=YouTubeSyncConfigResponse)
async def create_youtube_sync_config(
    data: YouTubeSyncConfigCreate,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> YouTubeSyncConfigResponse:
    """Create a YouTube playlist sync configuration.

    Args:
        data: Sync configuration request.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Created sync configuration.

    Raises:
        401: Not connected to YouTube.
        409: Config already exists.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Check if YouTube is connected
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail="not_connected_to_youtube")

    # Create sync config
    config = await repo.save_sync_config(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        playlist_id=data.playlist_id,
        playlist_name=data.playlist_name,
        sync_frequency=data.sync_frequency,
        is_active=True,
    )

    # Check if this was an update (config already exists)
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.id == config.id,
        )
    )
    db_config = result.scalar_one()

    return YouTubeSyncConfigResponse(
        playlist_id=db_config.resource_id,
        playlist_name=db_config.resource_name,
        sync_frequency=db_config.sync_frequency,
        is_active=bool(db_config.is_active),
        last_sync_at=db_config.last_sync_at.isoformat() if db_config.last_sync_at else None,
    )


@router.get("/integrations/youtube/configs", response_model=list[YouTubeSyncConfigResponse])
async def list_youtube_sync_configs(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> list[YouTubeSyncConfigResponse]:
    """List all YouTube sync configurations.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        List of sync configurations.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get sync configs
    repo = IntegrationRepository(db)
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)

    # Get last_sync_at from database
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
        )
    )
    db_configs = result.scalars().all()

    # Build a map for quick lookup
    db_config_map = {c.resource_id: c for c in db_configs}

    return [
        YouTubeSyncConfigResponse(
            playlist_id=c.playlist_id,
            playlist_name=c.playlist_name,
            sync_frequency=c.sync_frequency,
            is_active=c.is_active,
            last_sync_at=db_config_map.get(c.playlist_id, {}).last_sync_at.isoformat()
            if db_config_map.get(c.playlist_id) and db_config_map[c.playlist_id].last_sync_at
            else None,
        )
        for c in configs
    ]


@router.patch("/integrations/youtube/configs/{playlist_id}", response_model=YouTubeSyncConfigResponse)
async def update_youtube_sync_config(
    playlist_id: str,
    data: YouTubeSyncConfigUpdate,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> YouTubeSyncConfigResponse:
    """Update a YouTube sync configuration.

    Args:
        playlist_id: Playlist ID to update.
        data: Update request.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Updated sync configuration.

    Raises:
        401: Not authenticated.
        404: Config not found.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Check if config exists
    repo = IntegrationRepository(db)
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)

    existing = None
    for c in configs:
        if c.playlist_id == playlist_id:
            existing = c
            break

    if not existing:
        raise HTTPException(status_code=404, detail="sync_config_not_found")

    # Update config
    new_name = data.playlist_name if data.playlist_name is not None else existing.playlist_name
    new_frequency = data.sync_frequency if data.sync_frequency is not None else existing.sync_frequency
    new_active = data.is_active if data.is_active is not None else existing.is_active

    updated = await repo.save_sync_config(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        playlist_id=playlist_id,
        playlist_name=new_name,
        sync_frequency=new_frequency,
        is_active=new_active,
    )

    # Get last_sync_at from database
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
            IntegrationSyncConfig.resource_id == playlist_id,
        )
    )
    db_config = result.scalar_one_or_none()

    return YouTubeSyncConfigResponse(
        playlist_id=updated.resource_id,
        playlist_name=updated.resource_name,
        sync_frequency=updated.sync_frequency,
        is_active=bool(updated.is_active),
        last_sync_at=db_config.last_sync_at.isoformat() if db_config and db_config.last_sync_at else None,
    )


@router.delete("/integrations/youtube/configs/{playlist_id}")
async def delete_youtube_sync_config(
    playlist_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> dict:
    """Delete a YouTube sync configuration.

    Args:
        playlist_id: Playlist ID to delete.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Deletion confirmation.

    Raises:
        401: Not authenticated.
        404: Config not found.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Delete config
    repo = IntegrationRepository(db)
    deleted = await repo.delete_sync_config(user_id, Provider.YOUTUBE.value, playlist_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="sync_config_not_found")

    return {"message": "Sync configuration deleted successfully"}


@router.get("/integrations/youtube/logs", response_model=list[YouTubeSyncLogResponse])
async def list_youtube_sync_logs(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> list[YouTubeSyncLogResponse]:
    """List YouTube sync logs.

    Args:
        limit: Maximum number of logs to return.
        offset: Pagination offset.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        List of sync logs.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get sync logs
    repo = IntegrationRepository(db)
    logs = await repo.get_sync_logs(user_id, Provider.YOUTUBE.value, limit=limit, offset=offset)

    return [
        YouTubeSyncLogResponse(
            id=log.id,
            playlist_id=log.playlist_id,
            status=log.status,
            ingested_count=log.ingested_count,
            skipped_count=log.skipped_count,
            error_message=log.error_message,
            executed_at=log.executed_at.isoformat(),
        )
        for log in logs
    ]


@router.post("/integrations/youtube/sync")
async def trigger_youtube_sync(
    playlist_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> dict:
    """Trigger a YouTube playlist sync immediately.

    Args:
        playlist_id: Optional playlist ID to sync. If not provided, syncs all configured playlists.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Sync trigger confirmation.

    Raises:
        401: Not authenticated or not connected to YouTube.
    """
    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeClient
    from src.integrations.youtube.sync import YouTubeSyncService
    from src.ai.summarizer import Summarizer
    from src.data.repository import ContentRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get YouTube tokens
    integration_repo = IntegrationRepository(db)
    youtube_tokens = await integration_repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail="not_connected_to_youtube")

    # Create clients
    youtube_client = YouTubeClient(
        access_token=youtube_tokens.access_token,
        refresh_token=youtube_tokens.refresh_token,
        token_expires_at=youtube_tokens.expires_at,
    )

    content_repo = ContentRepository(db)

    # Initialize summarizer with API key
    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not summarizer_api_key:
        raise HTTPException(
            status_code=500,
            detail="anthropic_api_key_not_configured"
        )

    summarizer = Summarizer(api_key=summarizer_api_key)
    sync_service = YouTubeSyncService(
        youtube_client=youtube_client,
        content_repo=content_repo,
        integration_repo=integration_repo,
        summarizer=summarizer,
    )

    # Trigger sync (run in background to avoid blocking)
    async def do_sync():
        try:
            if playlist_id:
                result = await sync_service.sync_playlist(user_id, playlist_id)
                status = "success" if not result.errors else "partial"
                await integration_repo.log_sync(
                    user_id=user_id,
                    provider=Provider.YOUTUBE.value,
                    resource_id=playlist_id,
                    status=status,
                    ingested_count=result.ingested,
                    skipped_count=result.skipped,
                    error_message=None if not result.errors else str(result.errors),
                )
            else:
                results = await sync_service.sync_all_playlists(user_id)
                for pid, result in results.items():
                    status = "success" if not result.errors else "partial"
                    await integration_repo.log_sync(
                        user_id=user_id,
                        provider=Provider.YOUTUBE.value,
                        resource_id=pid,
                        status=status,
                        ingested_count=result.ingested,
                        skipped_count=result.skipped,
                        error_message=None if not result.errors else str(result.errors),
                    )
        except Exception as e:
            resource = playlist_id or "all"
            await integration_repo.log_sync(
                user_id=user_id,
                provider=Provider.YOUTUBE.value,
                resource_id=resource,
                status="failed",
                ingested_count=0,
                skipped_count=0,
                error_message=str(e),
            )

    # Schedule background task with exception handling and tracking
    import logging

    async def background_task_wrapper():
        """Wrapper to ensure exceptions don't crash the process."""
        current_task = asyncio.current_task()
        try:
            logging.info("YouTube sync background task started")
            await do_sync()
            logging.info("YouTube sync background task completed")
        except Exception as e:
            # Log unhandled exceptions (should not happen due to do_sync try/except)
            logging.error(f"Uncaught exception in YouTube sync background task: {e}")
        finally:
            if current_task:
                _background_tasks.discard(current_task)

    task = asyncio.create_task(background_task_wrapper())
    _background_tasks.add(task)
    logging.info(f"YouTube sync background task scheduled (task id: {id(task)})")

    return {
        "message": "Sync triggered",
        "playlist_id": playlist_id,
    }


@router.post("/integrations/youtube/connect")
async def connect_youtube(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> dict:
    """Initiate YouTube OAuth connection.

    Returns OAuth authorization URL for user to complete consent flow.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        OAuth authorization URL.

    Raises:
        401: Not authenticated.
    """
    import os
    from urllib.parse import urlencode

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="youtube_oauth_not_configured")

    # Build OAuth URL
    scope = "https://www.googleapis.com/auth/youtube.readonly"
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/youtube/callback")

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
                "access_type": "offline",
                "prompt": "consent",
                "state": str(user_id),  # Use user_id as state
            }
        )
    )

    return {"auth_url": auth_url}


@router.get("/integrations/youtube/callback")
async def youtube_callback(
    code: str = Query(...),
    state: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle YouTube OAuth callback.

    Exchanges authorization code for tokens and stores them.

    Args:
        code: Authorization code from YouTube.
        state: User ID (passed from connect endpoint).
        db: Database session.

    Returns:
        Connection confirmation.

    Raises:
        400: Invalid code or state.
    """
    import os
    from datetime import timedelta

    import httpx

    from src.integrations.repositories.integration import IntegrationRepository

    # Validate state (user_id)
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_state")

    # Get OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="youtube_oauth_not_configured")

    redirect_uri = os.getenv(
        "YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/youtube/callback"
    )

    # Exchange code for tokens
    async with async_client_context() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="youtube_auth_failed")

    token_data = response.json()

    # Store tokens
    repo = IntegrationRepository(db)
    expires_at = utc_now() + timedelta(seconds=token_data.get("expires_in", 3600))

    await repo.save_tokens(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
    )

    return {
        "message": "Connected to YouTube successfully",
        "user_id": user_id,
    }


@router.post("/integrations/youtube/disconnect")
async def disconnect_youtube(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> YouTubeDisconnectResponse:
    """Disconnect YouTube integration.

    Revokes OAuth tokens and deletes all sync configurations.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Disconnection confirmation.

    Raises:
        401: Not authenticated.
    """
    from sqlalchemy import delete

    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeClient

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get YouTube tokens
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if youtube_tokens:
        # Revoke tokens with YouTube
        client = YouTubeClient(
            access_token=youtube_tokens.access_token,
            refresh_token=youtube_tokens.refresh_token,
            token_expires_at=youtube_tokens.expires_at,
        )
        await client.disconnect()

        # Delete tokens from database
        await repo.delete_tokens(user_id, Provider.YOUTUBE.value)

    # Delete all sync configs
    await db.execute(
        delete(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
        )
    )

    await db.commit()

    return YouTubeDisconnectResponse(message="Disconnected from YouTube successfully")


# INT-002: LinkedIn Integration endpoints


@router.get("/integrations/linkedin/status", response_model=LinkedInConnectionStatus)
async def get_linkedin_status(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> LinkedInConnectionStatus:
    """Get LinkedIn connection status.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        LinkedIn connection status.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token (if provided)
    user_id = 1  # Default for MVP
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        auth_repo = AuthenticationRepository(db)
        token_record = await auth_repo.get_token_by_access_token(token)
        if token_record:
            user_id = token_record.user_id

    # Check if LinkedIn tokens exist
    repo = IntegrationRepository(db)
    tokens = await repo.get_tokens(user_id, Provider.LINKEDIN.value)

    if not tokens:
        return LinkedInConnectionStatus(is_connected=False)

    # Get last sync time
    last_sync = await repo.get_last_sync(user_id, Provider.LINKEDIN.value, "saved_posts")

    return LinkedInConnectionStatus(
        is_connected=True,
        last_sync_at=last_sync.isoformat() if last_sync else None,
    )


@router.post("/integrations/linkedin/disconnect", response_model=LinkedInDisconnectResponse)
async def disconnect_linkedin(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> LinkedInDisconnectResponse:
    """Disconnect LinkedIn integration.

    Revokes OAuth tokens and deletes all sync configurations.

    Args:
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        Disconnection confirmation.

    Raises:
        401: Not authenticated.
    """
    from sqlalchemy import delete

    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Delete tokens from database
    repo = IntegrationRepository(db)
    await repo.delete_tokens(user_id, Provider.LINKEDIN.value)

    # Delete all sync configs
    await db.execute(
        delete(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.LINKEDIN.value,
        )
    )

    await db.commit()

    return LinkedInDisconnectResponse(message="Disconnected from LinkedIn successfully")


@router.get("/integrations/linkedin/sync/logs", response_model=list[LinkedInSyncLogResponse])
async def get_linkedin_sync_logs(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    authorization: str | None = None,
) -> list[LinkedInSyncLogResponse]:
    """Get LinkedIn sync logs.

    Args:
        limit: Maximum number of logs to return.
        offset: Offset for pagination.
        db: Database session.
        authorization: Authorization header with Bearer token.

    Returns:
        List of sync logs.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get user_id from token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")

    token = authorization[7:]
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_id = token_record.user_id

    # Get sync logs
    repo = IntegrationRepository(db)
    logs = await repo.get_sync_logs(user_id, Provider.LINKEDIN.value, limit=limit, offset=offset)

    return [
        LinkedInSyncLogResponse(
            id=log.id,
            resource_id=log.resource_id,
            status=log.status,
            ingested_count=log.ingested_count,
            skipped_count=log.skipped_count,
            error_message=log.error_message,
            executed_at=log.executed_at.isoformat(),
        )
        for log in logs
    ]


@router.post("/integrations/linkedin/import", status_code=201, response_model=ShareResponse)
async def import_linkedin_post(
    data: LinkedInImportRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Import a single LinkedIn post by URL.

    This endpoint allows manual import of LinkedIn posts without OAuth.
    It fetches the post data from the public URL.

    Args:
        data: Import request with LinkedIn post URL.
        user_id: Current user ID (from auth).
        db: Database session.

    Returns:
        Share response with imported content.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.linkedin.client import LinkedInClient
    from src.integrations.linkedin.sync import LinkedInSyncService

    # Create LinkedIn client (no auth needed for public posts)
    client = LinkedInClient(access_token="")

    # Use sync service to import the post
    result = await LinkedInSyncService(db).sync_single_post(
        user_id=user_id,
        url=data.url,
        client=client,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "failed_to_import"))

    # Fetch the content for response
    content_id = result.get("content_id")
    if not content_id:
        raise HTTPException(status_code=500, detail="failed_to_get_content_id")

    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="content_not_found")

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
    min_score: float = Query(
        0.1, ge=0, le=1, description="Minimum relevance score threshold"
    ),
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


# ADV-002: Gamified Achievement System endpoints


@router.get("/achievements", response_model=AchievementsListResponse)
async def get_achievements(
    achievement_type: str | None = Query(
        None,
        pattern="^(streak|volume|diversity|curation)$",
        description="Filter by achievement type",
    ),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AchievementsListResponse:
    """Get all achievement definitions with user progress.

    Args:
        achievement_type: Optional filter by type
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        List of achievements with progress info
    """
    from src.ai.achievement_checker import AchievementChecker

    checker = AchievementChecker(db)
    stats = await checker._calculate_user_stats(user_id)
    achievements = await checker._achievement_repo.get_achievements_with_progress(
        user_id, stats
    )

    # Filter by type if specified
    if achievement_type:
        achievements = [a for a in achievements if a["type"] == achievement_type]

    return AchievementsListResponse(achievements=achievements)


@router.get("/achievements/stats", response_model=AchievementsStatsResponse)
async def get_achievements_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AchievementsStatsResponse:
    """Get user's achievement statistics.

    Args:
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Achievement statistics and progress
    """
    from src.ai.achievement_checker import AchievementChecker

    checker = AchievementChecker(db)
    stats = await checker._calculate_user_stats(user_id)

    # Get streak info
    streak = await checker._streak_repo.get_or_create_streak(user_id)

    # Get all definitions and user achievements
    all_definitions = await checker._achievement_repo.get_all_definitions()
    user_achievements = await checker._achievement_repo.get_user_achievements(user_id)

    total_unlocked = len(user_achievements)
    total_available = len(all_definitions)
    completion_percent = (
        int((total_unlocked / total_available) * 100)
        if total_available > 0
        else 0
    )

    # Build recent achievements list (last 5)
    recent = []
    for ua in user_achievements[:5]:
        definition = ua.achievement_definition
        recent.append(
            AchievementProgress(
                id=definition.id,
                key=definition.key,
                type=definition.type,
                name=definition.name,
                description=definition.description,
                icon=definition.icon,
                trigger_value=definition.trigger_value,
                is_unlocked=True,
                progress=definition.trigger_value,
                progress_percent=100,
                unlocked_at=ua.unlocked_at.isoformat(),
            )
        )

    return AchievementsStatsResponse(
        total_unlocked=total_unlocked,
        total_available=total_available,
        completion_percent=completion_percent,
        streak=StreakStats(
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            total_active_days=streak.total_active_days,
        ),
        recent_achievements=recent,
    )


@router.post("/achievements/check", response_model=CheckAchievementsResponse)
async def check_achievements(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckAchievementsResponse:
    """Check and award any newly unlocked achievements.

    Called after swipe actions to check for new achievements.

    Args:
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        List of newly unlocked achievements
    """
    from src.ai.achievement_checker import AchievementChecker

    checker = AchievementChecker(db)
    new_achievements = await checker.check_and_award(user_id)

    return CheckAchievementsResponse(
        new_achievements=[
            NewAchievement(
                id=ach["id"],
                name=ach["name"],
                icon=ach["icon"],
                unlocked_at=ach["unlocked_at"],
            )
            for ach in new_achievements
        ]
    )


# ============================================================================
# ADV-003: Smart Reminders Endpoints
# ============================================================================


@router.get("/reminders/preferences", response_model=ReminderPreferencesResponse)
async def get_reminder_preferences(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderPreferencesResponse:
    """Get user's reminder preferences.

    Args:
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Reminder preferences
    """
    from src.data.remind_repository import ReminderPreferenceRepository

    repo = ReminderPreferenceRepository(db)
    preference = await repo.get_or_create(user_id)

    return ReminderPreferencesResponse(
        is_enabled=bool(preference.is_enabled),
        preferred_time=preference.preferred_time.isoformat() if preference.preferred_time else None,
        frequency=preference.frequency,
        quiet_hours_start=preference.quiet_hours_start.isoformat() if preference.quiet_hours_start else None,
        quiet_hours_end=preference.quiet_hours_end.isoformat() if preference.quiet_hours_end else None,
        backlog_threshold=preference.backlog_threshold,
    )


@router.put("/reminders/preferences", response_model=ReminderPreferencesResponse)
async def update_reminder_preferences(
    update: ReminderPreferencesUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderPreferencesResponse:
    """Update user's reminder preferences.

    Args:
        update: Updated preferences
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Updated reminder preferences
    """
    from datetime import datetime

    from src.data.remind_repository import ReminderPreferenceRepository

    repo = ReminderPreferenceRepository(db)

    # Prepare update kwargs
    kwargs = {}
    if update.is_enabled is not None:
        kwargs["is_enabled"] = 1 if update.is_enabled else 0
    if update.preferred_time is not None:
        try:
            # Parse "HH:MM:SS" format
            time_parts = datetime.strptime(update.preferred_time, "%H:%M:%S").time()
            kwargs["preferred_time"] = datetime.combine(datetime.min, time_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid preferred_time format. Use HH:MM:SS")
    if update.frequency is not None:
        kwargs["frequency"] = update.frequency
    if update.quiet_hours_start is not None:
        try:
            time_parts = datetime.strptime(update.quiet_hours_start, "%H:%M:%S").time()
            kwargs["quiet_hours_start"] = datetime.combine(datetime.min, time_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid quiet_hours_start format. Use HH:MM:SS")
    if update.quiet_hours_end is not None:
        try:
            time_parts = datetime.strptime(update.quiet_hours_end, "%H:%M:%S").time()
            kwargs["quiet_hours_end"] = datetime.combine(datetime.min, time_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid quiet_hours_end format. Use HH:MM:SS")
    if update.backlog_threshold is not None:
        kwargs["backlog_threshold"] = update.backlog_threshold

    # Update or create
    preference = await repo.get(user_id)
    if preference:
        await repo.update(user_id, **kwargs)
    else:
        # Create with defaults if not exists
        defaults = {
            "is_enabled": 1,
            "preferred_time": datetime.combine(datetime.min, datetime.strptime("18:00:00", "%H:%M:%S").time()),
            "frequency": "daily",
            "backlog_threshold": 10,
        }
        preference = await repo.create(user_id, **{**defaults, **kwargs})

    return ReminderPreferencesResponse(
        is_enabled=bool(preference.is_enabled),
        preferred_time=preference.preferred_time.isoformat() if preference.preferred_time else None,
        frequency=preference.frequency,
        quiet_hours_start=preference.quiet_hours_start.isoformat() if preference.quiet_hours_start else None,
        quiet_hours_end=preference.quiet_hours_end.isoformat() if preference.quiet_hours_end else None,
        backlog_threshold=preference.backlog_threshold,
    )


@router.get("/reminders/suggest", response_model=ReminderSuggestionResponse)
async def get_reminder_suggestion(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderSuggestionResponse:
    """Get current reminder suggestion (if any).

    Args:
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Reminder suggestion or empty response
    """
    from src.ai.reminder_engine import ReminderEngine

    engine = ReminderEngine(db)
    suggestion = await engine.get_suggestion(user_id)

    if suggestion:
        return ReminderSuggestionResponse(
            has_reminder=True,
            reminder_type=suggestion.reminder_type.value,
            message=suggestion.message,
            priority=suggestion.priority.value,
            metadata=suggestion.metadata,
        )

    return ReminderSuggestionResponse(has_reminder=False)


@router.post("/reminders/respond", response_model=ReminderRespondResponse)
async def respond_to_reminder(
    request: ReminderRespondRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderRespondResponse:
    """Log user's response to a reminder.

    Args:
        request: Reminder ID and action (acted/dismissed)
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Confirmation response
    """
    from src.ai.reminder_engine import ReminderEngine

    engine = ReminderEngine(db)

    if request.action == "acted":
        success = await engine.log_action_taken(request.reminder_id)
    else:  # dismissed
        success = await engine.log_dismissed(request.reminder_id)

    if success:
        return ReminderRespondResponse(success=True, message="Response recorded")
    else:
        return ReminderRespondResponse(success=False, message="Reminder not found or already responded")
