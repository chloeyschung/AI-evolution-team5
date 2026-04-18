"""User domain router — /profile, /preferences, /user/statistics, /interests."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.repository import UserProfileRepository
from ...utils.datetime_utils import serialize_datetime
from ..dependencies import get_current_user
from ..schemas import (
    InterestTagRequest,
    InterestTagResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserStatisticsResponse,
)

router = APIRouter()


# DAT-002: User Profile & Preferences endpoints


def _resolve_profile_timezone(timezone: str | None) -> str:
    """Resolve profile timezone with backward-compatible fallback."""
    if timezone is None:
        return "UTC"
    normalized = timezone.strip()
    return normalized if normalized else "UTC"


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Get user profile.

    Auto-creates profile if it doesn't exist.
    """
    repo = UserProfileRepository(db)
    profile = await repo.get_or_create_profile(user_id=user_id)

    return UserProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        timezone=_resolve_profile_timezone(profile.timezone),
        created_at=serialize_datetime(profile.created_at),
        updated_at=serialize_datetime(profile.updated_at),
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update user profile."""
    repo = UserProfileRepository(db)
    profile = await repo.update_profile(
        user_id=user_id,
        display_name=data.display_name,
        avatar_url=data.avatar_url,
        bio=data.bio,
        timezone=data.timezone,
    )

    return UserProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        timezone=_resolve_profile_timezone(profile.timezone),
        created_at=serialize_datetime(profile.created_at),
        updated_at=serialize_datetime(profile.updated_at),
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Get user preferences.

    Auto-creates preferences with defaults if they don't exist.
    """
    repo = UserProfileRepository(db)
    preferences = await repo.get_preferences(user_id)

    return UserPreferencesResponse(
        theme=preferences.theme,
        notifications_enabled=bool(preferences.notifications_enabled),
        daily_goal=preferences.daily_goal,
        default_sort=preferences.default_sort,
    )


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    data: UserPreferencesUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Update user preferences."""
    repo = UserProfileRepository(db)
    preferences = await repo.update_preferences(
        user_id=user_id,
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
async def get_user_statistics(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserStatisticsResponse:
    """Get user statistics from swipe history.

    Returns aggregated metrics including swipe counts, retention rate, and streak.
    """
    repo = UserProfileRepository(db)
    stats = await repo.get_statistics(user_id)

    return UserStatisticsResponse(
        total_swipes=stats["total_swipes"],
        total_kept=stats["total_kept"],
        total_discarded=stats["total_discarded"],
        retention_rate=stats["retention_rate"],
        streak_days=stats["streak_days"],
        first_swipe_at=stats["first_swipe_at"].isoformat() + "Z" if stats["first_swipe_at"] else None,
        last_swipe_at=stats["last_swipe_at"].isoformat() + "Z" if stats["last_swipe_at"] else None,
    )


@router.get("/interests", response_model=list[str])
async def get_interests(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get all user interest tags."""
    repo = UserProfileRepository(db)
    return await repo.get_interest_tags(user_id)


@router.post("/interests", status_code=201, response_model=InterestTagResponse)
async def add_interest(
    data: InterestTagRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestTagResponse:
    """Add an interest tag.

    Tags are case-insensitive and unique per user.
    """
    repo = UserProfileRepository(db)
    tag = await repo.add_interest_tag(user_id, data.tag)

    return InterestTagResponse(id=tag.id, tag=tag.tag)


@router.delete("/interests/{tag}")
async def remove_interest(
    tag: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove an interest tag."""
    repo = UserProfileRepository(db)
    await repo.remove_interest_tag(user_id, tag)

    return {"message": f"Interest tag '{tag}' removed successfully"}
