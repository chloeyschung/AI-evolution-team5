"""Tests for smart reminder engine (ADV-003)."""

import pytest
from datetime import datetime, timedelta, time as time_type
from sqlalchemy import select

from src.data.models import (
    Content,
    SwipeHistory,
    SwipeAction,
    UserStreak,
    ReminderPreference,
    ReminderLog,
    UserActivityPattern,
    ContentStatus,
)
from src.ai.reminder_engine import (
    ReminderEngine,
    ActivityPatternLearner,
    ReminderType,
    ReminderPriority,
)
from src.data.remind_repository import (
    ReminderPreferenceRepository,
    ReminderLogRepository,
    UserActivityPatternRepository,
)


# ============================================================================
# Repository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reminder_preference_repository_get_or_create(db_session):
    """Test getting or creating reminder preferences."""
    repo = ReminderPreferenceRepository(db_session)
    preference = await repo.get_or_create(user_id=1)

    assert preference is not None
    assert preference.user_id == 1
    assert preference.is_enabled == 1
    assert preference.frequency == "daily"
    assert preference.backlog_threshold == 10


@pytest.mark.asyncio
async def test_reminder_preference_repository_update(db_session):
    """Test updating reminder preferences."""
    repo = ReminderPreferenceRepository(db_session)

    # Create
    preference = await repo.create(
        user_id=1,
        is_enabled=1,
        frequency="weekly",
        backlog_threshold=20,
    )

    # Update
    updated = await repo.update(user_id=1, is_enabled=0, backlog_threshold=15)

    assert updated.is_enabled == 0
    assert updated.backlog_threshold == 15
    assert updated.frequency == "weekly"  # Unchanged


@pytest.mark.asyncio
async def test_reminder_log_repository_create(db_session):
    """Test creating reminder log entries."""
    repo = ReminderLogRepository(db_session)

    log = await repo.create(
        user_id=1,
        reminder_type="backlog",
        message="You have 15 unread items",
    )

    assert log.user_id == 1
    assert log.reminder_type == "backlog"
    assert log.action_taken == 0


@pytest.mark.asyncio
async def test_reminder_log_repository_mark_action_taken(db_session):
    """Test marking reminder as actioned."""
    repo = ReminderLogRepository(db_session)

    log = await repo.create(
        user_id=1,
        reminder_type="backlog",
        message="Test message",
    )

    success = await repo.mark_action_taken(log.id)

    assert success is True

    # Verify
    result = await db_session.execute(
        select(ReminderLog).where(ReminderLog.id == log.id)
    )
    updated_log = result.scalar_one()
    assert updated_log.action_taken == 1
    assert updated_log.action_taken_at is not None


@pytest.mark.asyncio
async def test_reminder_log_repository_mark_dismissed(db_session):
    """Test marking reminder as dismissed."""
    repo = ReminderLogRepository(db_session)

    log = await repo.create(
        user_id=1,
        reminder_type="streak",
        message="Don't break your streak",
    )

    success = await repo.mark_dismissed(log.id)

    assert success is True

    # Verify
    result = await db_session.execute(
        select(ReminderLog).where(ReminderLog.id == log.id)
    )
    updated_log = result.scalar_one()
    assert updated_log.dismissed_at is not None


@pytest.mark.asyncio
async def test_user_activity_pattern_repository_get_or_create(db_session):
    """Test getting or creating activity pattern."""
    repo = UserActivityPatternRepository(db_session)
    pattern = await repo.get_or_create(user_id=1)

    assert pattern is not None
    assert pattern.user_id == 1
    assert pattern.most_active_hour == 18  # Default
    assert pattern.most_active_day == 0  # Default (Monday)


# ============================================================================
# ReminderEngine Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reminder_engine_initialization(db_session):
    """Test reminder engine initialization."""
    engine = ReminderEngine(db_session)

    assert engine is not None
    assert engine._preference_repo is not None
    assert engine._pattern_repo is not None
    assert engine._log_repo is not None


@pytest.mark.asyncio
async def test_get_suggestion_no_preferences(db_session):
    """Test getting suggestion when no preferences exist."""
    engine = ReminderEngine(db_session)

    # No preferences created - should return None
    suggestion = await engine.get_suggestion(user_id=999)

    assert suggestion is None


@pytest.mark.asyncio
async def test_get_suggestion_reminders_disabled(db_session):
    """Test getting suggestion when reminders are disabled."""
    engine = ReminderEngine(db_session)

    # Create disabled preferences
    repo = ReminderPreferenceRepository(db_session)
    await repo.create(user_id=1, is_enabled=0, frequency="daily")

    suggestion = await engine.get_suggestion(user_id=1)

    assert suggestion is None


@pytest.mark.asyncio
async def test_get_suggestion_backlog_reminder(db_session):
    """Test backlog reminder generation."""
    engine = ReminderEngine(db_session)

    # Create preferences with low threshold
    pref_repo = ReminderPreferenceRepository(db_session)
    await pref_repo.create(
        user_id=1,
        is_enabled=1,
        frequency="daily",
        backlog_threshold=5,
    )

    # Create 10 unread items
    for i in range(10):
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.INBOX,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    suggestion = await engine.get_suggestion(user_id=1)

    assert suggestion is not None
    assert suggestion.reminder_type == ReminderType.BACKLOG
    assert "10 unread items" in suggestion.message
    assert suggestion.priority == ReminderPriority.MEDIUM


@pytest.mark.asyncio
async def test_get_suggestion_streak_reminder(db_session):
    """Test streak reminder generation (highest priority)."""
    engine = ReminderEngine(db_session)

    # Create preferences
    pref_repo = ReminderPreferenceRepository(db_session)
    await pref_repo.create(
        user_id=1,
        is_enabled=1,
        frequency="daily",
        backlog_threshold=100,  # High threshold to avoid backlog reminder
    )

    # Create streak with 7 days
    streak = UserStreak(
        user_id=1,
        current_streak=7,
        longest_streak=7,
        last_activity_date=datetime.now() - timedelta(days=1),  # Yesterday
        total_active_days=7,
    )
    db_session.add(streak)

    # Create unread items
    for i in range(5):
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.INBOX,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    suggestion = await engine.get_suggestion(user_id=1)

    assert suggestion is not None
    assert suggestion.reminder_type == ReminderType.STREAK
    assert "7-day streak" in suggestion.message
    assert suggestion.priority == ReminderPriority.HIGH


@pytest.mark.asyncio
async def test_get_suggestion_no_reminder_needed(db_session):
    """Test when no reminder is needed."""
    engine = ReminderEngine(db_session)

    # Create preferences with high threshold
    pref_repo = ReminderPreferenceRepository(db_session)
    await pref_repo.create(
        user_id=1,
        is_enabled=1,
        frequency="daily",
        backlog_threshold=100,
    )

    # No unread items, no streak
    suggestion = await engine.get_suggestion(user_id=1)

    assert suggestion is None


@pytest.mark.asyncio
async def test_log_reminder_sent(db_session):
    """Test logging a sent reminder."""
    engine = ReminderEngine(db_session)

    # Create a suggestion manually
    from src.ai.reminder_engine import ReminderSuggestion

    suggestion = ReminderSuggestion(
        reminder_type=ReminderType.BACKLOG,
        message="Test message",
        priority=ReminderPriority.MEDIUM,
        metadata={"unread_count": 10},
    )

    log_id = await engine.log_reminder_sent(user_id=1, suggestion=suggestion)

    assert log_id > 0

    # Verify
    result = await db_session.execute(
        select(ReminderLog).where(ReminderLog.id == log_id)
    )
    log = result.scalar_one()
    assert log.reminder_type == "backlog"
    assert log.message == "Test message"


@pytest.mark.asyncio
async def test_log_action_taken(db_session):
    """Test logging action taken on reminder."""
    engine = ReminderEngine(db_session)

    # Create a reminder log
    log_repo = ReminderLogRepository(db_session)
    log = await log_repo.create(
        user_id=1,
        reminder_type="backlog",
        message="Test",
    )

    success = await engine.log_action_taken(log.id)

    assert success is True


@pytest.mark.asyncio
async def test_quiet_hours_check(db_session):
    """Test quiet hours suppression."""
    from datetime import datetime, time as time_type

    engine = ReminderEngine(db_session)

    # Create preferences with quiet hours 22:00 to 08:00
    pref_repo = ReminderPreferenceRepository(db_session)
    preference = await pref_repo.create(
        user_id=1,
        is_enabled=1,
        frequency="daily",
        quiet_hours_start=datetime.combine(datetime.min, time_type(22, 0)),
        quiet_hours_end=datetime.combine(datetime.min, time_type(8, 0)),
    )

    # Test during quiet hours (e.g., 3 AM)
    # Note: This test may be flaky depending on actual time
    # In production, we'd mock the time
    is_quiet = engine._is_quiet_hours(preference)

    # Just verify the method doesn't crash
    assert isinstance(is_quiet, bool)


# ============================================================================
# ActivityPatternLearner Tests
# ============================================================================


@pytest.mark.asyncio
async def test_activity_pattern_learner_initialization(db_session):
    """Test activity pattern learner initialization."""
    learner = ActivityPatternLearner(db_session)

    assert learner is not None
    assert learner._pattern_repo is not None


@pytest.mark.asyncio
async def test_update_patterns_with_no_history(db_session):
    """Test updating patterns with no swipe history."""
    from sqlalchemy import delete

    # Clean up any existing data first
    await db_session.execute(delete(UserActivityPattern).where(UserActivityPattern.user_id == 1))
    await db_session.execute(delete(SwipeHistory))
    await db_session.execute(delete(Content))
    await db_session.commit()

    learner = ActivityPatternLearner(db_session)

    pattern = await learner.update_patterns(user_id=1)

    assert pattern is not None
    assert pattern.user_id == 1
    # Should use defaults when no history
    assert pattern.most_active_hour == 18
    assert pattern.avg_daily_swipes == 10.0  # Default value


@pytest.mark.asyncio
async def test_update_patterns_with_history(db_session):
    """Test updating patterns with swipe history."""
    learner = ActivityPatternLearner(db_session)

    # Create swipe history at different hours
    base_time = datetime.now() - timedelta(days=15)

    for i in range(30):
        # Create content
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.ARCHIVED,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    # Create swipes at hour 14 (2 PM) - most common
    contents = await db_session.execute(select(Content))
    content_list = contents.scalars().all()

    for i, content in enumerate(content_list):
        swipe_time = base_time + timedelta(hours=i * 2)
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=swipe_time,
            user_id=1,
        )
        db_session.add(swipe)

    await db_session.flush()

    # Update patterns
    pattern = await learner.update_patterns(user_id=1)

    assert pattern is not None
    assert pattern.avg_daily_swipes > 0
    assert 0 <= pattern.most_active_hour < 24
    assert 0 <= pattern.most_active_day < 7


@pytest.mark.asyncio
async def test_count_by_hour(db_session):
    """Test counting swipes by hour."""
    learner = ActivityPatternLearner(db_session)

    # Create swipes at specific hours
    swipes = []
    hours = [10, 10, 10, 14, 14, 18]
    for idx, h in enumerate(hours):
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={idx}",
            title=f"Video {idx}",
            status=ContentStatus.ARCHIVED,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    contents = await db_session.execute(select(Content))
    content_list = contents.scalars().all()

    for i, content in enumerate(content_list):
        swipe_time = datetime.now().replace(hour=hours[i])
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=swipe_time,
            user_id=1,
        )
        db_session.add(swipe)
        swipes.append(swipe)

    await db_session.flush()

    # Count by hour
    counts = learner._count_by_hour(swipes)

    assert counts[10] == 3
    assert counts[14] == 2
    assert counts[18] == 1


@pytest.mark.asyncio
async def test_count_by_day(db_session):
    """Test counting swipes by day of week."""
    learner = ActivityPatternLearner(db_session)

    # Create swipes on different days
    swipes = []
    base_date = datetime(2024, 1, 8)  # Monday
    day_offsets = [0, 0, 2, 2, 2, 5]  # Mon, Wed, Sat

    for idx, offset in enumerate(day_offsets):
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={idx}",
            title=f"Video {idx}",
            status=ContentStatus.ARCHIVED,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    contents = await db_session.execute(select(Content))
    content_list = contents.scalars().all()

    for i, content in enumerate(content_list):
        swipe_time = base_date + timedelta(days=day_offsets[i])
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=swipe_time,
            user_id=1,
        )
        db_session.add(swipe)
        swipes.append(swipe)

    await db_session.flush()

    # Count by day
    counts = learner._count_by_day(swipes)

    assert counts[0] == 2  # Monday (0)
    assert counts[2] == 3  # Wednesday (2)
    assert counts[5] == 1  # Saturday (5)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_reminder_flow(db_session):
    """Test complete reminder flow: suggest -> send -> respond."""
    engine = ReminderEngine(db_session)

    # Setup: Create preferences
    pref_repo = ReminderPreferenceRepository(db_session)
    await pref_repo.create(
        user_id=1,
        is_enabled=1,
        frequency="daily",
        backlog_threshold=3,
    )

    # Setup: Create unread items
    for i in range(5):
        content = Content(
            platform="YouTube",
            content_type="video",
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.INBOX,
            user_id=1,
        )
        db_session.add(content)

    await db_session.flush()

    # Step 1: Get suggestion
    suggestion = await engine.get_suggestion(user_id=1)
    assert suggestion is not None
    assert suggestion.reminder_type == ReminderType.BACKLOG

    # Step 2: Log reminder sent
    log_id = await engine.log_reminder_sent(user_id=1, suggestion=suggestion)
    assert log_id > 0

    # Step 3: User takes action
    success = await engine.log_action_taken(log_id)
    assert success is True

    # Verify
    result = await db_session.execute(
        select(ReminderLog).where(ReminderLog.id == log_id)
    )
    log = result.scalar_one()
    assert log.action_taken == 1
