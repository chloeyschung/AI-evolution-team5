"""Tests for API routes."""

import pytest


class TestContentEndpoints:
    """Tests for content API endpoints."""

    async def test_create_content(self, authenticated_client):
        """Test creating new content."""
        response = await authenticated_client.post(
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

    async def test_create_content_minimal(self, authenticated_client):
        """Test creating content with minimal fields."""
        response = await authenticated_client.post(
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

    async def test_list_content(self, authenticated_client):
        """Test listing all content returns pagination wrapper."""
        response = await authenticated_client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_more" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["has_more"], bool)

    async def test_list_content_with_limit(self, authenticated_client):
        """Test listing content with limit parameter returns pagination wrapper."""
        response = await authenticated_client.get("/api/v1/content?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_more" in data
        assert len(data["items"]) <= 10

    async def test_list_content_has_more_false_when_fewer_than_limit(self, authenticated_client):
        """Test has_more=False when items returned is less than limit."""
        # Create 2 items
        for i in range(2):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/has-more-test-{i}",
                },
            )

        # Request with limit=100 — we'll get fewer than limit items
        response = await authenticated_client.get("/api/v1/content?limit=100")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_more" in data
        # Fewer items than limit → has_more must be False
        assert len(data["items"]) < 100
        assert data["has_more"] is False

    async def test_list_content_has_more_true_when_full_page(self, authenticated_client):
        """Test has_more=True when exactly limit items are returned."""
        # Create 3 items, then request limit=3 — full page returned
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/full-page-test-{i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_more" in data
        # Full page returned → has_more must be True
        assert len(data["items"]) == 3
        assert data["has_more"] is True

    async def test_list_content_includes_total_field(self, authenticated_client):
        """Test GET /content response includes total count field (iOS compliance)."""
        # Create 2 items
        for i in range(2):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/total-field-test-{i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data, "Response must contain 'total' field for iOS progress indicators"
        assert isinstance(data["total"], int)
        assert data["total"] >= 2

    async def test_list_content_includes_next_offset_field(self, authenticated_client):
        """Test GET /content response includes next_offset field (iOS compliance)."""
        # Create 4 items, request limit=2 → has_more=True → next_offset=2
        for i in range(4):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/next-offset-test-{i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "next_offset" in data, "Response must contain 'next_offset' field for iOS pagination"
        # has_more=True → next_offset must be non-null integer
        assert data["has_more"] is True
        assert data["next_offset"] == 2
        assert "next_cursor" in data

    async def test_list_content_next_offset_none_when_no_more(self, authenticated_client):
        """Test next_offset is None when has_more=False (no more pages)."""
        # Create 2 items, request limit=100 → has_more=False → next_offset=None
        for i in range(2):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/no-more-test-{i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content?limit=100&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "next_offset" in data
        assert data["has_more"] is False
        assert data["next_offset"] is None
        assert "next_cursor" in data

    async def test_list_content_cursor_mode_returns_next_cursor(self, authenticated_client):
        """Cursor mode should support forward pagination and return next_cursor."""
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/list-cursor-test-{i}",
                },
            )

        page1 = await authenticated_client.get("/api/v1/content?limit=2")
        assert page1.status_code == 200
        page1_data = page1.json()
        assert page1_data["next_cursor"] is not None

        page2 = await authenticated_client.get(
            f"/api/v1/content?limit=2&cursor={page1_data['next_cursor']}"
        )
        assert page2.status_code == 200
        page2_data = page2.json()
        assert page2_data["next_offset"] is None

        page1_ids = {item["id"] for item in page1_data["items"]}
        page2_ids = {item["id"] for item in page2_data["items"]}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_list_content_malformed_cursor_returns_400(self, authenticated_client):
        """Malformed cursor should return structured HTTP 400 for /content."""
        response = await authenticated_client.get("/api/v1/content?cursor=not-a-cursor")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_cursor"

    async def test_list_content_total_matches_actual_count(self, authenticated_client):
        """Test total matches the actual number of items across pages."""
        # Create exactly 5 items
        for i in range(5):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/total-match-test-{i}",
                },
            )

        # Fetch page 1 with limit=3
        response = await authenticated_client.get("/api/v1/content?limit=3&offset=0")
        assert response.status_code == 200
        data = response.json()
        total = data["total"]
        assert total >= 5  # At least the 5 we created (test DB may have prior items)
        # next_offset should advance by len(items)
        assert data["next_offset"] == 3


class TestSwipeEndpoints:
    """Tests for swipe API endpoints."""

    async def test_record_swipe_keep(self, authenticated_client):
        """Test recording KEEP swipe action."""
        # First create a content
        create_response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content_id"] == content_id
        assert data["action"] == "keep"

    async def test_record_swipe_discard(self, authenticated_client):
        """Test recording DISCARD swipe action."""
        # First create a content
        create_response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test-2",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "discard"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "discard"


class TestPendingContentEndpoints:
    """Tests for pending content API endpoints."""

    async def test_get_pending_content(self, authenticated_client):
        """Test getting pending content (no swipe history)."""
        # Create contents
        await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-1",
            },
        )
        await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-2",
            },
        )

        # Get pending content
        response = await authenticated_client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    async def test_get_pending_empty(self, authenticated_client):
        """Test getting pending content when all content is swiped."""
        # Create and swipe content
        create_response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swiped-unique-test",
            },
        )
        content_id = create_response.json()["id"]

        # Swipe the content
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get pending content
        response = await authenticated_client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    async def test_get_pending_limit(self, authenticated_client):
        """Test pending content with limit parameter."""
        # Create multiple contents
        for i in range(10):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/limit-test-{i}",
                },
            )

        # Get pending content with limit
        response = await authenticated_client.get("/api/v1/content/pending?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5


class TestContentDetailEndpoint:
    """Tests for GET /content/{content_id} endpoint (UX-003)."""

    async def test_get_content_detail(self, authenticated_client):
        """Test getting content detail with all fields."""
        # Create content with summary
        create_response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "YouTube",
                "content_type": "video",
                "url": "https://youtube.com/watch?v=test123",
                "title": "Test Video",
                "author": "Test Author",
            },
        )
        content_id = create_response.json()["id"]

        # Get content detail
        response = await authenticated_client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content_id
        assert data["platform"] == "YouTube"
        assert data["content_type"] == "video"
        assert data["url"] == "https://youtube.com/watch?v=test123"
        assert data["title"] == "Test Video"
        assert data["author"] == "Test Author"
        assert data["status"] == "inbox"
        assert data["summary"] is None
        assert data["swipe_history"] is None
        assert "created_at" in data

    async def test_get_content_detail_not_found(self, authenticated_client):
        """Test getting non-existent content returns 404."""
        response = await authenticated_client.get("/api/v1/content/9999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    async def test_get_content_detail_with_swipe_history(self, authenticated_client):
        """Test getting content detail with swipe history."""
        # Create content
        create_response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-detail",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get content detail
        response = await authenticated_client.get(f"/api/v1/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["swipe_history"] is not None
        assert data["swipe_history"]["action"] == "keep"
        assert "swiped_at" in data["swipe_history"]


class TestHealthCheck:
    """Tests for health check endpoint."""

    async def test_root_endpoint(self, async_client):
        """Test root endpoint returns health check."""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "briefly-api"
