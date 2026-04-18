"""AI domain router — /achievements/*, /reminders/*."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants import ErrorCode
from ...data.database import get_db
from ..dependencies import get_current_user
from ..schemas import (
    AchievementProgress,
    AchievementsListResponse,
    AchievementsStatsResponse,
    CheckAchievementsResponse,
    NewAchievement,
    ReminderPreferencesResponse,
    ReminderPreferencesUpdate,
    ReminderRespondRequest,
    ReminderRespondResponse,
    ReminderSuggestionResponse,
    StreakStats,
)

router = APIRouter()


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
    achievements = await checker._achievement_repo.get_achievements_with_progress(user_id, stats)

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

    # Get streak info
    streak = await checker._streak_repo.get_or_create_streak(user_id)

    # Get all definitions and user achievements
    all_definitions = await checker._achievement_repo.get_all_definitions()
    user_achievements = await checker._achievement_repo.get_user_achievements(user_id)

    total_unlocked = len(user_achievements)
    total_available = len(all_definitions)
    completion_percent = int((total_unlocked / total_available) * 100) if total_available > 0 else 0

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
            raise HTTPException(status_code=400, detail=f"{ErrorCode.INVALID_TIME_FORMAT}: preferred_time") from None
    if update.frequency is not None:
        kwargs["frequency"] = update.frequency
    if update.quiet_hours_start is not None:
        try:
            time_parts = datetime.strptime(update.quiet_hours_start, "%H:%M:%S").time()
            kwargs["quiet_hours_start"] = datetime.combine(datetime.min, time_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{ErrorCode.INVALID_TIME_FORMAT}: quiet_hours_start") from None
    if update.quiet_hours_end is not None:
        try:
            time_parts = datetime.strptime(update.quiet_hours_end, "%H:%M:%S").time()
            kwargs["quiet_hours_end"] = datetime.combine(datetime.min, time_parts)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{ErrorCode.INVALID_TIME_FORMAT}: quiet_hours_end") from None
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
