"""Tests for API routes."""

import pytest


class TestContentEndpoints:
    """Tests for content API endpoints."""

    async def test_create_content(self, async_client):
        """Test creating new content."""
        response = await async_client.post(
            "/api/v1/content",
            json={
                "platform": "YouTube",
                "content_type": "video",
                "url": "https://youtube.com/watch?v=test123",
                "title": "Test Video",
                "author": "Test Author",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "YouTube"
        assert data["content_type"] == "video"
        assert data["url"] == "https://youtube.com/watch?v=test123"
        assert data["id"] is not None

    async def test_create_content_minimal(self, async_client):
        """Test creating content with minimal fields."""
        response = await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Web",
                "content_type": "article",
                "url": "https://example.com/article",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "Web"
        assert data["title"] is None
        assert data["author"] is None

    async def test_list_content(self, async_client):
        """Test listing all content."""
        response = await async_client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_content_with_limit(self, async_client):
        """Test listing content with limit parameter."""
        response = await async_client.get("/api/v1/content?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10


class TestSwipeEndpoints:
    """Tests for swipe API endpoints."""

    async def test_record_swipe_keep(self, async_client):
        """Test recording KEEP swipe action."""
        # First create a content
        create_response = await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = await async_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content_id"] == content_id
        assert data["action"] == "keep"

    async def test_record_swipe_discard(self, async_client):
        """Test recording DISCARD swipe action."""
        # First create a content
        create_response = await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test-2",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = await async_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "discard"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "discard"


class TestPendingContentEndpoints:
    """Tests for pending content API endpoints."""

    async def test_get_pending_content(self, async_client):
        """Test getting pending content (no swipe history)."""
        # Create contents
        await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-1",
            },
        )
        await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-2",
            },
        )

        # Get pending content
        response = await async_client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_get_pending_empty(self, async_client):
        """Test getting pending content when all content is swiped."""
        # Create and swipe content
        create_response = await async_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swiped",
            },
        )
        content_id = create_response.json()["id"]

        # Swipe the content
        await async_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get pending content
        response = await async_client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_get_pending_limit(self, async_client):
        """Test pending content with limit parameter."""
        # Create multiple contents
        for i in range(10):
            await async_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/limit-test-{i}",
                },
            )

        # Get pending content with limit
        response = await async_client.get("/api/v1/content/pending?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestHealthCheck:
    """Tests for health check endpoint."""

    async def test_root_endpoint(self, async_client):
        """Test root endpoint returns health check."""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "briefly-api"
