"""Tests for paginated envelope on /pending, /kept, /discarded, /search endpoints.

TDD: these tests are written BEFORE the implementation.
They assert that these endpoints return PaginatedContentResponse shape:
  { items: list, has_more: bool, total: int, next_offset: int | None }
"""

import pytest


PAGINATION_KEYS = {"items", "has_more", "total", "next_offset"}


class TestPendingPaginatedEnvelope:
    """GET /content/pending must return PaginatedContentResponse."""

    async def test_pending_returns_pagination_envelope(self, authenticated_client):
        """Response must have items, has_more, total, next_offset keys."""
        response = await authenticated_client.get("/api/v1/content/pending")
        assert response.status_code == 200
        data = response.json()
        assert PAGINATION_KEYS <= data.keys(), (
            f"Missing keys: {PAGINATION_KEYS - data.keys()}"
        )

    async def test_pending_items_is_list(self, authenticated_client):
        """items must be a list."""
        response = await authenticated_client.get("/api/v1/content/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)

    async def test_pending_total_is_int(self, authenticated_client):
        """total must be an integer."""
        response = await authenticated_client.get("/api/v1/content/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total"], int)

    async def test_pending_has_more_is_bool(self, authenticated_client):
        """has_more must be a boolean."""
        response = await authenticated_client.get("/api/v1/content/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["has_more"], bool)

    async def test_pending_total_reflects_count(self, authenticated_client):
        """total must reflect actual count of pending content."""
        # Create 2 pending items
        for i in range(2):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/pending-count-test-{i}",
                    "title": f"Pending Count Test {i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content/pending?limit=1")
        assert response.status_code == 200
        data = response.json()
        # total should be >= 2 (not just the limit=1 page)
        assert data["total"] >= 2

    async def test_pending_next_offset_when_has_more(self, authenticated_client):
        """next_offset must be set when has_more is True."""
        # Create 3 items so limit=2 triggers has_more
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/pending-offset-test-{i}",
                    "title": f"Pending Offset Test {i}",
                },
            )

        response = await authenticated_client.get("/api/v1/content/pending?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        if data["has_more"]:
            assert data["next_offset"] is not None
            assert data["next_offset"] == 2


class TestKeptPaginatedEnvelope:
    """GET /content/kept must return PaginatedContentResponse."""

    async def test_kept_returns_pagination_envelope(self, authenticated_client):
        """Response must have items, has_more, total, next_offset keys."""
        response = await authenticated_client.get("/api/v1/content/kept")
        assert response.status_code == 200
        data = response.json()
        assert PAGINATION_KEYS <= data.keys(), (
            f"Missing keys: {PAGINATION_KEYS - data.keys()}"
        )

    async def test_kept_items_is_list(self, authenticated_client):
        """items must be a list."""
        response = await authenticated_client.get("/api/v1/content/kept")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)

    async def test_kept_total_is_int(self, authenticated_client):
        """total must be an integer."""
        response = await authenticated_client.get("/api/v1/content/kept")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total"], int)

    async def test_kept_total_reflects_count(self, authenticated_client):
        """total must reflect total kept items regardless of limit."""
        # Create and keep 3 items
        for i in range(3):
            post_resp = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/kept-count-{i}",
                    "title": f"Kept Count Test {i}",
                },
            )
            content_id = post_resp.json()["id"]
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        response = await authenticated_client.get("/api/v1/content/kept?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3


class TestDiscardedPaginatedEnvelope:
    """GET /content/discarded must return PaginatedContentResponse."""

    async def test_discarded_returns_pagination_envelope(self, authenticated_client):
        """Response must have items, has_more, total, next_offset keys."""
        response = await authenticated_client.get("/api/v1/content/discarded")
        assert response.status_code == 200
        data = response.json()
        assert PAGINATION_KEYS <= data.keys(), (
            f"Missing keys: {PAGINATION_KEYS - data.keys()}"
        )

    async def test_discarded_items_is_list(self, authenticated_client):
        """items must be a list."""
        response = await authenticated_client.get("/api/v1/content/discarded")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)

    async def test_discarded_total_is_int(self, authenticated_client):
        """total must be an integer."""
        response = await authenticated_client.get("/api/v1/content/discarded")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total"], int)

    async def test_discarded_total_reflects_count(self, authenticated_client):
        """total must reflect total discarded items regardless of limit."""
        # Create and discard 3 items
        for i in range(3):
            post_resp = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/discarded-count-{i}",
                    "title": f"Discarded Count Test {i}",
                },
            )
            content_id = post_resp.json()["id"]
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "discard"},
            )

        response = await authenticated_client.get("/api/v1/content/discarded?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3


class TestSearchPaginatedEnvelope:
    """GET /search must return PaginatedContentResponse."""

    async def test_search_returns_pagination_envelope(self, authenticated_client):
        """Response must have items, has_more, total, next_offset keys."""
        response = await authenticated_client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert PAGINATION_KEYS <= data.keys(), (
            f"Missing keys: {PAGINATION_KEYS - data.keys()}"
        )

    async def test_search_items_is_list(self, authenticated_client):
        """items must be a list."""
        response = await authenticated_client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)

    async def test_search_total_is_int(self, authenticated_client):
        """total must be an integer."""
        response = await authenticated_client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total"], int)

    async def test_search_total_reflects_count(self, authenticated_client):
        """total must reflect total matching items regardless of limit."""
        # Create 3 searchable items
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/search-envelope-{i}",
                    "title": f"SearchEnvelopeTest article {i}",
                },
            )

        response = await authenticated_client.get(
            "/api/v1/search?q=SearchEnvelopeTest&limit=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3

    async def test_search_next_offset_when_has_more(self, authenticated_client):
        """next_offset must be set when has_more is True."""
        for i in range(3):
            await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Web",
                    "content_type": "article",
                    "url": f"https://example.com/search-next-offset-{i}",
                    "title": f"SearchNextOffsetTest article {i}",
                },
            )

        response = await authenticated_client.get(
            "/api/v1/search?q=SearchNextOffsetTest&limit=2&offset=0"
        )
        assert response.status_code == 200
        data = response.json()
        if data["has_more"]:
            assert data["next_offset"] is not None
            assert data["next_offset"] == 2
