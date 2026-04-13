"""API tests for user profile and preferences endpoints (DAT-002)."""

import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.api.app import app
from src.data.models import Base, UserProfile, UserPreferences, InterestTag, SwipeHistory, Content


# Create test database using SQLite with async support
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_briefly_async.db"
test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncTestingSessionLocal = async_sessionmaker(
    test_async_engine, autocommit=False, autoflush=False
)


# Override the app's database dependency with async session
from src.data import database as db_module


async def async_get_db():
    """Async database dependency for testing."""
    async with AsyncTestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


app.dependency_overrides[db_module.get_db] = async_get_db


@pytest.fixture(scope="module", autouse=True)
async def create_test_tables():
    """Create test tables before running tests."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function", autouse=True)
async def clear_test_data():
    """Clear test data before each test."""
    async with AsyncTestingSessionLocal() as db:
        await db.execute(delete(InterestTag))
        await db.execute(delete(UserPreferences))
        await db.execute(delete(UserProfile))
        await db.execute(delete(SwipeHistory))
        await db.execute(delete(Content))
        await db.commit()


@pytest.fixture
async def client():
    """Create async test client."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestProfileEndpoints:
    """Tests for /profile endpoints."""

    async def test_get_profile_creates_default(self, client):
        """Test GET /profile creates default profile if none exists."""
        response = await client.get("/api/v1/profile")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["display_name"] is None
        assert data["avatar_url"] is None
        assert data["bio"] is None
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_profile_returns_existing(self, client):
        """Test GET /profile returns existing profile."""
        # First request creates profile
        response1 = await client.get("/api/v1/profile")
        profile_id = response1.json()["id"]

        # Second request should return same profile
        response2 = await client.get("/api/v1/profile")
        assert response2.status_code == 200
        assert response2.json()["id"] == profile_id

    async def test_update_profile(self, client):
        """Test PATCH /profile updates profile fields."""
        # Update profile
        response = await client.patch(
            "/api/v1/profile",
            json={"display_name": "Test User", "bio": "Test bio"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test User"
        assert data["bio"] == "Test bio"

    async def test_update_profile_partial(self, client):
        """Test PATCH /profile with partial update."""
        # First create profile with all fields
        await client.patch(
            "/api/v1/profile",
            json={"display_name": "Original", "bio": "Original bio", "avatar_url": "https://example.com/avatar.jpg"}
        )

        # Update only display_name
        response = await client.patch(
            "/api/v1/profile",
            json={"display_name": "Updated"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated"
        assert data["bio"] == "Original bio"  # Should remain unchanged
        assert data["avatar_url"] == "https://example.com/avatar.jpg"  # Should remain unchanged


class TestPreferencesEndpoints:
    """Tests for /preferences endpoints."""

    async def test_get_preferences_creates_default(self, client):
        """Test GET /preferences creates default preferences."""
        response = await client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "system"
        assert data["notifications_enabled"] is True
        assert data["daily_goal"] == 20
        assert data["default_sort"] == "recency"

    async def test_update_preferences(self, client):
        """Test PATCH /preferences updates all fields."""
        response = await client.patch(
            "/api/v1/preferences",
            json={"theme": "dark", "notifications_enabled": False, "daily_goal": 50, "default_sort": "platform"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["notifications_enabled"] is False
        assert data["daily_goal"] == 50
        assert data["default_sort"] == "platform"

    async def test_update_preferences_partial(self, client):
        """Test PATCH /preferences with partial update."""
        # First create preferences
        await client.get("/api/v1/preferences")

        # Update only theme
        response = await client.patch(
            "/api/v1/preferences",
            json={"theme": "light"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["notifications_enabled"] is True  # Should remain default
        assert data["daily_goal"] == 20  # Should remain default

    async def test_update_preferences_invalid_daily_goal(self, client):
        """Test PATCH /preferences rejects invalid daily_goal."""
        response = await client.patch(
            "/api/v1/preferences",
            json={"daily_goal": -10}
        )

        assert response.status_code == 422  # Validation error


class TestStatisticsEndpoints:
    """Tests for /user/statistics endpoint."""

    async def test_get_statistics_empty(self, client):
        """Test GET /user/statistics with no swipe history."""
        response = await client.get("/api/v1/user/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_swipes"] == 0
        assert data["total_kept"] == 0
        assert data["total_discarded"] == 0
        assert data["retention_rate"] == 0.0
        assert data["streak_days"] == 0
        assert data["first_swipe_at"] is None
        assert data["last_swipe_at"] is None


class TestInterestsEndpoints:
    """Tests for /interests endpoints."""

    async def test_get_interests_empty(self, client):
        """Test GET /interests with no tags."""
        response = await client.get("/api/v1/interests")

        assert response.status_code == 200
        assert response.json() == []

    async def test_add_interest(self, client):
        """Test POST /interests adds a tag."""
        response = await client.post(
            "/api/v1/interests",
            json={"tag": "Technology"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tag"] == "technology"  # Should be normalized to lowercase

    async def test_add_interest_case_insensitive(self, client):
        """Test POST /interests is case-insensitive."""
        # Add tag
        await client.post("/api/v1/interests", json={"tag": "Technology"})

        # Add same tag with different case
        response = await client.post(
            "/api/v1/interests",
            json={"tag": "TECHNOLOGY"}
        )

        assert response.status_code == 201
        # Should return existing tag
        assert response.json()["tag"] == "technology"

    async def test_add_interest_trim_whitespace(self, client):
        """Test POST /interests trims whitespace."""
        response = await client.post(
            "/api/v1/interests",
            json={"tag": "  Design  "}
        )

        assert response.status_code == 201
        assert response.json()["tag"] == "design"

    async def test_get_interests_after_add(self, client):
        """Test GET /interests returns added tags."""
        # Add multiple tags
        await client.post("/api/v1/interests", json={"tag": "Technology"})
        await client.post("/api/v1/interests", json={"tag": "Design"})
        await client.post("/api/v1/interests", json={"tag": "Productivity"})

        response = await client.get("/api/v1/interests")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert "technology" in data
        assert "design" in data
        assert "productivity" in data

    async def test_remove_interest(self, client):
        """Test DELETE /interests/{tag} removes a tag."""
        # Add tag
        await client.post("/api/v1/interests", json={"tag": "TestTag"})

        # Verify it exists
        tags = await client.get("/api/v1/interests")
        assert "testtag" in tags.json()

        # Remove tag
        response = await client.delete("/api/v1/interests/TestTag")

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's removed
        tags = await client.get("/api/v1/interests")
        assert "testtag" not in tags.json()

    async def test_remove_interest_case_insensitive(self, client):
        """Test DELETE /interests/{tag} is case-insensitive."""
        # Add tag
        await client.post("/api/v1/interests", json={"tag": "TestTag"})

        # Remove with different case
        response = await client.delete("/api/v1/interests/testtag")

        assert response.status_code == 200
