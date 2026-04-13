"""Tests for user profile and preferences repository."""

import pytest
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.data.models import Base, UserProfile, UserPreferences, InterestTag, SwipeHistory, SwipeAction, Content, Theme, DefaultSort
from src.data.repository import UserProfileRepository


# Test database setup - use same DB as other API tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_briefly_async.db"
test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncTestingSessionLocal = async_sessionmaker(
    test_async_engine, autocommit=False, autoflush=False
)


@pytest.fixture(scope="module", autouse=True)
async def create_test_tables():
    """Create test tables before running tests."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function", autouse=True)
async def clean_test_data():
    """Clean test data before each test."""
    async with AsyncTestingSessionLocal() as db:
        await db.execute(delete(InterestTag))
        await db.execute(delete(UserPreferences))
        await db.execute(delete(UserProfile))
        await db.execute(delete(SwipeHistory))
        await db.execute(delete(Content))
        await db.commit()


@pytest.fixture
async def db_session():
    """Provide a database session for tests."""
    async with AsyncTestingSessionLocal() as db:
        yield db
        await db.rollback()


class TestUserProfileRepository:
    """Tests for UserProfileRepository."""

    async def test_get_or_create_profile_creates_new(self, db_session):
        """Test that get_or_create_profile creates a new profile when none exists."""
        repo = UserProfileRepository(db_session)
        profile = await repo.get_or_create_profile()

        assert profile is not None
        assert profile.id is not None
        assert profile.display_name is None
        assert profile.avatar_url is None
        assert profile.bio is None
        assert profile.created_at is not None
        assert profile.updated_at is not None

    async def test_get_or_create_profile_returns_existing(self, db_session):
        """Test that get_or_create_profile returns existing profile."""
        repo = UserProfileRepository(db_session)

        # Create first profile
        profile1 = await repo.get_or_create_profile()

        # Get profile again
        profile2 = await repo.get_or_create_profile()

        assert profile1.id == profile2.id

    async def test_update_profile_updates_fields(self, db_session):
        """Test that update_profile updates the specified fields."""
        repo = UserProfileRepository(db_session)

        # Get or create profile
        profile = await repo.get_or_create_profile()
        original_created_at = profile.created_at

        # Update profile
        updated = await repo.update_profile(
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            bio="Test bio"
        )

        assert updated.display_name == "Test User"
        assert updated.avatar_url == "https://example.com/avatar.jpg"
        assert updated.bio == "Test bio"
        assert updated.created_at == original_created_at
        assert updated.updated_at >= original_created_at

    async def test_update_profile_partial_update(self, db_session):
        """Test that update_profile only updates provided fields."""
        repo = UserProfileRepository(db_session)

        # Create profile with some data
        profile = await repo.update_profile(display_name="Original", bio="Original bio")

        # Update only display_name
        updated = await repo.update_profile(display_name="Updated")

        assert updated.display_name == "Updated"
        assert updated.bio == "Original bio"  # Should remain unchanged


class TestUserPreferencesRepository:
    """Tests for user preferences repository."""

    async def test_get_preferences_creates_with_defaults(self, db_session):
        """Test that get_preferences creates preferences with defaults."""
        repo = UserProfileRepository(db_session)
        preferences = await repo.get_preferences()

        assert preferences is not None
        assert preferences.user_id == 1
        assert preferences.theme == Theme.SYSTEM
        assert preferences.notifications_enabled == 1  # SQLite stores bool as int
        assert preferences.daily_goal == 20
        assert preferences.default_sort == DefaultSort.RECENCY

    async def test_get_preferences_returns_existing(self, db_session):
        """Test that get_preferences returns existing preferences."""
        repo = UserProfileRepository(db_session)

        # Create preferences
        prefs1 = await repo.get_preferences()
        await repo.update_preferences(theme=Theme.DARK, daily_goal=30)

        # Get preferences again
        prefs2 = await repo.get_preferences()

        assert prefs1.id == prefs2.id
        assert prefs2.theme == Theme.DARK
        assert prefs2.daily_goal == 30

    async def test_update_preferences_updates_fields(self, db_session):
        """Test that update_preferences updates the specified fields."""
        repo = UserProfileRepository(db_session)

        # Get preferences
        preferences = await repo.get_preferences()
        original_updated_at = preferences.updated_at

        # Update preferences
        updated = await repo.update_preferences(
            theme=Theme.DARK,
            notifications_enabled=False,
            daily_goal=50,
            default_sort=DefaultSort.PLATFORM
        )

        assert updated.theme == Theme.DARK
        assert updated.notifications_enabled == 0  # SQLite stores bool as int
        assert updated.daily_goal == 50
        assert updated.default_sort == DefaultSort.PLATFORM
        assert updated.updated_at >= original_updated_at

    async def test_update_preferences_partial_update(self, db_session):
        """Test that update_preferences only updates provided fields."""
        repo = UserProfileRepository(db_session)

        # Create preferences
        preferences = await repo.get_preferences()

        # Update only theme
        updated = await repo.update_preferences(theme=Theme.LIGHT)

        assert updated.theme == Theme.LIGHT
        assert updated.notifications_enabled == 1  # Should remain default (SQLite bool as int)
        assert updated.daily_goal == 20  # Should remain default
        assert updated.default_sort == DefaultSort.RECENCY  # Should remain default


class TestUserStatisticsRepository:
    """Tests for user statistics repository."""

    async def test_get_statistics_empty_history(self, db_session):
        """Test statistics with empty swipe history."""
        repo = UserProfileRepository(db_session)
        stats = await repo.get_statistics()

        assert stats["total_swipes"] == 0
        assert stats["total_kept"] == 0
        assert stats["total_discarded"] == 0
        assert stats["retention_rate"] == 0.0
        assert stats["streak_days"] == 0
        assert stats["first_swipe_at"] is None
        assert stats["last_swipe_at"] is None

    async def test_get_statistics_with_swipes(self, db_session):
        """Test statistics calculation with swipe history."""
        repo = UserProfileRepository(db_session)

        # Create test content
        content = Content(
            platform="Test",
            content_type="article",
            url="https://example.com/test"
        )
        db_session.add(content)
        await db_session.commit()
        await db_session.refresh(content)

        # Create swipe history
        now = datetime.now(timezone.utc)
        swipes = [
            SwipeHistory(content_id=content.id, action=SwipeAction.KEEP, swiped_at=now - timedelta(hours=1)),
            SwipeHistory(content_id=content.id, action=SwipeAction.KEEP, swiped_at=now - timedelta(hours=2)),
            SwipeHistory(content_id=content.id, action=SwipeAction.DISCARD, swiped_at=now - timedelta(hours=3)),
        ]
        db_session.add_all(swipes)
        await db_session.commit()

        # Get statistics
        stats = await repo.get_statistics()

        assert stats["total_swipes"] == 3
        assert stats["total_kept"] == 2
        assert stats["total_discarded"] == 1
        assert stats["retention_rate"] == 2/3
        assert stats["streak_days"] >= 1

    async def test_get_statistics_retention_rate(self, db_session):
        """Test retention rate calculation."""
        repo = UserProfileRepository(db_session)

        # Create test content
        content = Content(
            platform="Test",
            content_type="article",
            url="https://example.com/test"
        )
        db_session.add(content)
        await db_session.commit()
        await db_session.refresh(content)

        # Create 10 swipes: 6 keep, 4 discard
        now = datetime.now(timezone.utc)
        for i in range(6):
            db_session.add(SwipeHistory(
                content_id=content.id,
                action=SwipeAction.KEEP,
                swiped_at=now - timedelta(hours=i)
            ))
        for i in range(4):
            db_session.add(SwipeHistory(
                content_id=content.id,
                action=SwipeAction.DISCARD,
                swiped_at=now - timedelta(hours=10+i)
            ))
        await db_session.commit()

        stats = await repo.get_statistics()

        assert stats["total_swipes"] == 10
        assert stats["total_kept"] == 6
        assert stats["total_discarded"] == 4
        assert stats["retention_rate"] == 0.6


class TestInterestTagRepository:
    """Tests for interest tag repository."""

    async def test_add_interest_tag_creates_new(self, db_session):
        """Test adding a new interest tag."""
        repo = UserProfileRepository(db_session)
        tag = await repo.add_interest_tag("Technology")

        assert tag is not None
        assert tag.user_id == 1
        assert tag.tag == "technology"  # Should be normalized to lowercase

    async def test_add_interest_tag_case_insensitive(self, db_session):
        """Test that adding duplicate tag (different case) returns existing."""
        repo = UserProfileRepository(db_session)

        # Add tag
        tag1 = await repo.add_interest_tag("Technology")

        # Add same tag with different case
        tag2 = await repo.add_interest_tag("TECHNOLOGY")

        assert tag1.id == tag2.id

    async def test_add_interest_tag_trims_whitespace(self, db_session):
        """Test that tag whitespace is trimmed."""
        repo = UserProfileRepository(db_session)

        tag1 = await repo.add_interest_tag("  Design  ")
        tag2 = await repo.add_interest_tag("Design")

        assert tag1.id == tag2.id

    async def test_remove_interest_tag(self, db_session):
        """Test removing an interest tag."""
        repo = UserProfileRepository(db_session)

        # Add tag
        await repo.add_interest_tag("Technology")

        # Verify it exists
        tags = await repo.get_interest_tags()
        assert "technology" in tags

        # Remove tag
        await repo.remove_interest_tag("Technology")

        # Verify it's removed
        tags = await repo.get_interest_tags()
        assert "technology" not in tags

    async def test_get_interest_tags(self, db_session):
        """Test getting all interest tags."""
        repo = UserProfileRepository(db_session)

        # Add multiple tags
        await repo.add_interest_tag("Technology")
        await repo.add_interest_tag("Design")
        await repo.add_interest_tag("Productivity")

        tags = await repo.get_interest_tags()

        assert len(tags) == 3
        assert "technology" in tags
        assert "design" in tags
        assert "productivity" in tags
