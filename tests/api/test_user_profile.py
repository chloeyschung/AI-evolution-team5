"""API tests for user profile and preferences endpoints (DAT-002)."""

import pytest
import httpx
from httpx import ASGITransport

from src.api.app import app


@pytest.fixture
async def client(async_client):
    """Create async test client using shared fixture."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestProfileEndpoints:
    """Tests for /profile endpoints."""

    async def test_get_profile_creates_default(self, authenticated_client):
        """Test GET /profile creates default profile if none exists."""
        response = await authenticated_client.get("/api/v1/profile")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["display_name"] is None
        assert data["avatar_url"] is None
        assert data["bio"] is None
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_profile_returns_existing(self, authenticated_client):
        """Test GET /profile returns existing profile."""
        # First request creates profile
        response1 = await authenticated_client.get("/api/v1/profile")
        profile_id = response1.json()["id"]

        # Second request should return same profile
        response2 = await authenticated_client.get("/api/v1/profile")
        assert response2.status_code == 200
        assert response2.json()["id"] == profile_id

    async def test_update_profile(self, authenticated_client):
        """Test PATCH /profile updates profile fields."""
        # Update profile
        response = await authenticated_client.patch(
            "/api/v1/profile",
            json={"display_name": "Test User", "bio": "Test bio"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test User"
        assert data["bio"] == "Test bio"

    async def test_update_profile_partial(self, authenticated_client):
        """Test PATCH /profile with partial update."""
        # First create profile with all fields
        await authenticated_client.patch(
            "/api/v1/profile",
            json={"display_name": "Original", "bio": "Original bio", "avatar_url": "https://example.com/avatar.jpg"}
        )

        # Update only display_name
        response = await authenticated_client.patch(
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

    async def test_get_preferences_creates_default(self, authenticated_client):
        """Test GET /preferences creates default preferences."""
        response = await authenticated_client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "system"
        assert data["notifications_enabled"] is True
        assert data["daily_goal"] == 20
        assert data["default_sort"] == "recency"

    async def test_update_preferences(self, authenticated_client):
        """Test PATCH /preferences updates all fields."""
        response = await authenticated_client.patch(
            "/api/v1/preferences",
            json={"theme": "dark", "notifications_enabled": False, "daily_goal": 50, "default_sort": "platform"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["notifications_enabled"] is False
        assert data["daily_goal"] == 50
        assert data["default_sort"] == "platform"

    async def test_update_preferences_partial(self, authenticated_client):
        """Test PATCH /preferences with partial update."""
        # First create preferences
        await authenticated_client.get("/api/v1/preferences")

        # Update only theme
        response = await authenticated_client.patch(
            "/api/v1/preferences",
            json={"theme": "light"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["notifications_enabled"] is True  # Should remain default
        assert data["daily_goal"] == 20  # Should remain default

    async def test_update_preferences_invalid_daily_goal(self, authenticated_client):
        """Test PATCH /preferences rejects invalid daily_goal."""
        response = await authenticated_client.patch(
            "/api/v1/preferences",
            json={"daily_goal": -10}
        )

        assert response.status_code == 422  # Validation error


class TestStatisticsEndpoints:
    """Tests for /user/statistics endpoint."""

    async def test_get_statistics_empty(self, authenticated_client):
        """Test GET /user/statistics with no swipe history."""
        response = await authenticated_client.get("/api/v1/user/statistics")

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

    async def test_get_interests_empty(self, authenticated_client):
        """Test GET /interests with no tags."""
        response = await authenticated_client.get("/api/v1/interests")

        assert response.status_code == 200
        assert response.json() == []

    async def test_add_interest(self, authenticated_client):
        """Test POST /interests adds a tag."""
        response = await authenticated_client.post(
            "/api/v1/interests",
            json={"tag": "Technology"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tag"] == "technology"  # Should be normalized to lowercase

    async def test_add_interest_case_insensitive(self, authenticated_client):
        """Test POST /interests is case-insensitive."""
        # Add tag
        await authenticated_client.post("/api/v1/interests", json={"tag": "Technology"})

        # Add same tag with different case
        response = await authenticated_client.post(
            "/api/v1/interests",
            json={"tag": "TECHNOLOGY"}
        )

        assert response.status_code == 201
        # Should return existing tag
        assert response.json()["tag"] == "technology"

    async def test_add_interest_trim_whitespace(self, authenticated_client):
        """Test POST /interests trims whitespace."""
        response = await authenticated_client.post(
            "/api/v1/interests",
            json={"tag": "  Design  "}
        )

        assert response.status_code == 201
        assert response.json()["tag"] == "design"

    async def test_get_interests_after_add(self, authenticated_client):
        """Test GET /interests returns added tags."""
        # Add multiple tags
        await authenticated_client.post("/api/v1/interests", json={"tag": "Technology"})
        await authenticated_client.post("/api/v1/interests", json={"tag": "Design"})
        await authenticated_client.post("/api/v1/interests", json={"tag": "Productivity"})

        response = await authenticated_client.get("/api/v1/interests")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert "technology" in data
        assert "design" in data
        assert "productivity" in data

    async def test_remove_interest(self, authenticated_client):
        """Test DELETE /interests/{tag} removes a tag."""
        # Add tag
        await authenticated_client.post("/api/v1/interests", json={"tag": "TestTag"})

        # Verify it exists
        tags = await authenticated_client.get("/api/v1/interests")
        assert "testtag" in tags.json()

        # Remove tag
        response = await authenticated_client.delete("/api/v1/interests/TestTag")

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's removed
        tags = await authenticated_client.get("/api/v1/interests")
        assert "testtag" not in tags.json()

    async def test_remove_interest_case_insensitive(self, authenticated_client, db):
        """Test DELETE /interests/{tag} is case-insensitive."""
        # Add tag
        await authenticated_client.post("/api/v1/interests", json={"tag": "TestTag"})

        # Remove with different case
        response = await authenticated_client.delete("/api/v1/interests/testtag")

        assert response.status_code == 200
