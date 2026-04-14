"""Tests for achievement checker (ADV-002)."""

import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from src.ai.achievement_checker import AchievementChecker
from src.data.achievement_repository import AchievementRepository, StreakRepository
from src.data.models import Content, ContentStatus, SwipeAction, SwipeHistory
from src.data.seed_achievements import seed_achievements, ACHIEVEMENT_DEFINITIONS


@pytest.mark.asyncio
async def test_seed_achievements(db_session):
    """Test seeding achievement definitions."""
    count = await seed_achievements(db_session)
    assert count == len(ACHIEVEMENT_DEFINITIONS)

    # Verify achievements were created
    from sqlalchemy import select
    from src.data.models import AchievementDefinition

    result = await db_session.execute(select(AchievementDefinition))
    achievements = result.scalars().all()
    assert len(achievements) == len(ACHIEVEMENT_DEFINITIONS)


@pytest.mark.asyncio
async def test_seed_achievements_idempotent(db_session):
    """Test that seeding is idempotent."""
    # First seed
    count1 = await seed_achievements(db_session)
    assert count1 == len(ACHIEVEMENT_DEFINITIONS)

    # Second seed should return 0
    count2 = await seed_achievements(db_session)
    assert count2 == 0


@pytest.mark.asyncio
async def test_achievement_checker_initialization(db_session):
    """Test achievement checker initialization."""
    checker = AchievementChecker(db_session)
    assert checker._achievement_repo is not None
    assert checker._streak_repo is not None
    assert checker._content_repo is not None
    assert checker._swipe_repo is not None


@pytest.mark.asyncio
async def test_calculate_user_stats_empty(db_session):
    """Test user stats calculation with no data."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    stats = await checker._calculate_user_stats(user_id=999)

    assert stats["current_streak"] == 0
    assert stats["total_swipes"] == 0
    assert stats["platform_count"] == 0
    assert stats["kept_count"] == 0


@pytest.mark.asyncio
async def test_calculate_user_stats_with_data(db_session):
    """Test user stats calculation with swipe data."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    # Create content with swipe history
    for i in range(5):
        content = Content(
            platform="YouTube" if i < 3 else "LinkedIn",
            content_type="video",
            url=f"https://example.com/{i}",
            title=f"Content {i}",
            status=ContentStatus.ARCHIVED,
        )
        db_session.add(content)
        await db_session.flush()

        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=datetime.now(timezone.utc) - timedelta(days=i),
        )
        db_session.add(swipe)

    await db_session.commit()

    stats = await checker._calculate_user_stats(user_id=1)

    assert stats["total_swipes"] == 5
    assert stats["platform_count"] == 2  # YouTube and LinkedIn
    assert stats["kept_count"] == 5


@pytest.mark.asyncio
async def test_check_streak_achievements(db_session):
    """Test streak achievement checking."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    # Create streak
    streak = await checker._streak_repo.get_or_create_streak(user_id=1)
    streak.current_streak = 7
    await db_session.flush()

    stats = {"current_streak": 7, "total_swipes": 0, "platform_count": 0, "kept_count": 0}

    achievements = await checker._check_streak_achievements(user_id=1, stats=stats)

    # Should unlock streak_1, streak_3, streak_7
    unlocked_names = [a["name"] for a in achievements]
    assert "First Steps" in unlocked_names
    assert "Building Momentum" in unlocked_names
    assert "On Fire" in unlocked_names
    assert "Unstoppable" not in unlocked_names  # Needs 14 days


@pytest.mark.asyncio
async def test_check_volume_achievements(db_session):
    """Test volume achievement checking."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    stats = {"current_streak": 0, "total_swipes": 50, "platform_count": 0, "kept_count": 0}

    achievements = await checker._check_volume_achievements(user_id=1, stats=stats)

    # Should unlock volume_10, volume_50
    unlocked_names = [a["name"] for a in achievements]
    assert "Beginner" in unlocked_names
    assert "Enthusiast" in unlocked_names
    assert "Scholar" not in unlocked_names  # Needs 100


@pytest.mark.asyncio
async def test_check_diversity_achievements(db_session):
    """Test diversity achievement checking."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    stats = {"current_streak": 0, "total_swipes": 0, "platform_count": 5, "kept_count": 0}

    achievements = await checker._check_diversity_achievements(user_id=1, stats=stats)

    # Should unlock diversity_3, diversity_5
    unlocked_names = [a["name"] for a in achievements]
    assert "Explorer" in unlocked_names
    assert "Polyglot" in unlocked_names
    assert "Omni" not in unlocked_names  # Needs 8


@pytest.mark.asyncio
async def test_check_curation_achievements(db_session):
    """Test curation achievement checking."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    stats = {"current_streak": 0, "total_swipes": 0, "platform_count": 0, "kept_count": 100}

    achievements = await checker._check_curation_achievements(user_id=1, stats=stats)

    # Should unlock curation_20, curation_100
    unlocked_names = [a["name"] for a in achievements]
    assert "Curator" in unlocked_names
    assert "Collector" in unlocked_names
    assert "Archivist" not in unlocked_names  # Needs 500


@pytest.mark.asyncio
async def test_award_achievement_idempotent(db_session):
    """Test that achievements are not awarded twice."""
    await seed_achievements(db_session)
    repo = AchievementRepository(db_session)

    # Get first achievement
    from sqlalchemy import select
    from src.data.models import AchievementDefinition

    result = await db_session.execute(select(AchievementDefinition).limit(1))
    definition = result.scalar_one()

    # Award first time
    awarded1 = await repo.award_achievement(user_id=1, achievement_id=definition.id)
    assert awarded1 is not None

    # Award second time (should return None)
    awarded2 = await repo.award_achievement(user_id=1, achievement_id=definition.id)
    assert awarded2 is None


@pytest.mark.asyncio
async def test_update_streak_consecutive_days(db_session):
    """Test streak update for consecutive days."""
    await seed_achievements(db_session)
    repo = StreakRepository(db_session)

    # Day 1
    result1 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 1))
    assert result1["current_streak"] == 1

    # Day 2
    result2 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 2))
    assert result2["current_streak"] == 2

    # Day 3
    result3 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 3))
    assert result3["current_streak"] == 3
    assert result3["longest_streak"] == 3


@pytest.mark.asyncio
async def test_update_streak_gap_in_days(db_session):
    """Test streak reset when there's a gap."""
    await seed_achievements(db_session)
    repo = StreakRepository(db_session)

    # Day 1
    result1 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 1))
    assert result1["current_streak"] == 1

    # Day 2
    result2 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 2))
    assert result2["current_streak"] == 2

    # Day 5 (gap of 2 days)
    result3 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 5))
    assert result3["current_streak"] == 1  # Reset to 1
    assert result3["longest_streak"] == 2  # Previous longest preserved


@pytest.mark.asyncio
async def test_update_streak_same_day(db_session):
    """Test that same-day activity doesn't increment streak."""
    await seed_achievements(db_session)
    repo = StreakRepository(db_session)

    # Day 1
    result1 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 1))
    assert result1["current_streak"] == 1

    # Same day again
    result2 = await repo.update_streak(user_id=1, activity_date=date(2024, 1, 1))
    assert result2["current_streak"] == 1  # Still 1


@pytest.mark.asyncio
async def test_get_achievements_with_progress(db_session):
    """Test getting achievements with progress info."""
    await seed_achievements(db_session)
    repo = AchievementRepository(db_session)

    stats = {
        "current_streak": 5,
        "total_swipes": 25,
        "platform_count": 2,
        "kept_count": 15,
    }

    achievements = await repo.get_achievements_with_progress(user_id=1, stats=stats)

    assert len(achievements) == len(ACHIEVEMENT_DEFINITIONS)

    # Check progress calculation
    streak_7 = next(a for a in achievements if a["key"] == "streak_7")
    assert streak_7["progress"] == 5
    assert streak_7["progress_percent"] == int((5 / 7) * 100)  # 71%

    volume_10 = next(a for a in achievements if a["key"] == "volume_10")
    assert volume_10["progress"] == 25
    assert volume_10["progress_percent"] == 100  # Capped at 100%


@pytest.mark.asyncio
async def test_check_and_award_all_types(db_session):
    """Test checking and awarding all achievement types."""
    await seed_achievements(db_session)
    checker = AchievementChecker(db_session)

    # Create data that should unlock multiple achievements
    for i in range(15):
        platform = "YouTube" if i < 8 else "LinkedIn" if i < 12 else "Twitter"
        content = Content(
            platform=platform,
            content_type="video",
            url=f"https://example.com/{i}",
            title=f"Content {i}",
            status=ContentStatus.ARCHIVED,
        )
        db_session.add(content)
        await db_session.flush()

        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=datetime.now(timezone.utc) - timedelta(days=i % 10),
        )
        db_session.add(swipe)

    await db_session.commit()

    # Update streak
    for day in range(1, 8):
        await checker._streak_repo.update_streak(user_id=1, activity_date=date(2024, 1, day))

    # Check and award
    new_achievements = await checker.check_and_award(user_id=1)

    # Should have unlocked several achievements
    assert len(new_achievements) > 0

    # Verify achievement structure
    for ach in new_achievements:
        assert "id" in ach
        assert "name" in ach
        assert "icon" in ach
        assert "unlocked_at" in ach
