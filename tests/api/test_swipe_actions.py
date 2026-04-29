"""Tests for UX-002 Swipe Actions API endpoints."""

import pytest


class TestBatchSwipeEndpoints:
    """Tests for batch swipe recording."""

    async def test_record_batch_swipes(self, authenticated_client):
        """Test recording multiple swipe actions atomically."""
        # Create multiple contents
        content_ids = []
        for i in range(5):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/batch-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Record batch swipe
        response = await authenticated_client.post(
            "/api/v1/swipe/batch",
            json={
                "actions": [
                    {"content_id": content_ids[0], "action": "keep"},
                    {"content_id": content_ids[1], "action": "discard"},
                    {"content_id": content_ids[2], "action": "keep"},
                ]
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["recorded"] == 3
        assert len(data["results"]) == 3

        # Verify all actions were recorded correctly
        actions = {r["content_id"]: r["action"] for r in data["results"]}
        assert actions[content_ids[0]] == "keep"
        assert actions[content_ids[1]] == "discard"
        assert actions[content_ids[2]] == "keep"

    async def test_batch_discard_soft_deletes_like_single_discard(self, authenticated_client):
        """Batch DISCARD must move content to trash, matching single DISCARD semantics."""
        response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/batch-discard-trash",
            },
        )
        content_id = response.json()["id"]

        response = await authenticated_client.post(
            "/api/v1/swipe/batch",
            json={"actions": [{"content_id": content_id, "action": "discard"}]},
        )
        assert response.status_code == 201

        trash_response = await authenticated_client.get("/api/v1/content/trash")
        assert trash_response.status_code == 200
        trash_ids = [item["id"] for item in trash_response.json()["items"]]
        assert content_id in trash_ids

    async def test_record_single_swipe_still_works(self, authenticated_client):
        """Test backward compatibility with single swipe API."""
        # Create content
        response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/single-swipe",
            },
        )
        content_id = response.json()["id"]

        # Record single swipe (old format)
        response = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content_id"] == content_id
        assert data["action"] == "keep"
        assert "id" in data  # Returns created record ID


class TestKeptContentEndpoints:
    """Tests for GET /content/kept endpoint."""

    async def test_get_kept_content(self, authenticated_client):
        """Test retrieving kept content."""
        # Create and keep some content
        kept_ids = []
        discarded_ids = []
        for i in range(5):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/kept-{i}",
                },
            )
            kept_ids.append(response.json()["id"])

            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/discard-{i}",
                },
            )
            discarded_ids.append(response.json()["id"])

        # Keep the first batch
        for content_id in kept_ids:
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Discard the second batch
        for content_id in discarded_ids:
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "discard"},
            )

        # Get kept content
        response = await authenticated_client.get("/api/v1/content/kept")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

        # Verify only kept content is returned
        returned_ids = [c["id"] for c in data["items"]]
        for content_id in kept_ids:
            assert content_id in returned_ids
        for content_id in discarded_ids:
            assert content_id not in returned_ids

    async def test_get_kept_empty(self, authenticated_client):
        """Test empty kept list when no content is kept."""
        # Create content but don't keep it
        await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/no-keep",
            },
        )

        # Get kept content
        response = await authenticated_client.get("/api/v1/content/kept")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    async def test_get_kept_pagination(self, authenticated_client):
        """Test pagination for kept content."""
        # Create and keep 10 content items
        for i in range(10):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/paginate-{i}",
                },
            )
            content_id = response.json()["id"]
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Get with limit=5
        response = await authenticated_client.get("/api/v1/content/kept?limit=5")
        data = response.json()
        assert len(data["items"]) == 5

        # Get with offset=5
        response = await authenticated_client.get("/api/v1/content/kept?limit=5&offset=5")
        data = response.json()
        assert len(data["items"]) == 5


class TestDiscardedContentEndpoints:
    """Tests for GET /content/discarded endpoint."""

    async def test_get_discarded_content(self, authenticated_client):
        """Test retrieving discarded content."""
        # Create and discard some content
        discarded_ids = []
        kept_ids = []
        for i in range(5):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/discard-test-{i}",
                },
            )
            discarded_ids.append(response.json()["id"])

            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/keep-test-{i}",
                },
            )
            kept_ids.append(response.json()["id"])

        # Discard the first batch
        for content_id in discarded_ids:
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "discard"},
            )

        # Keep the second batch
        for content_id in kept_ids:
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Get discarded content
        response = await authenticated_client.get("/api/v1/content/discarded")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

        # Verify only discarded content is returned
        returned_ids = [c["id"] for c in data["items"]]
        for content_id in discarded_ids:
            assert content_id in returned_ids
        for content_id in kept_ids:
            assert content_id not in returned_ids

    async def test_get_discarded_empty(self, authenticated_client):
        """Test empty discarded list when no content is discarded."""
        # Create content but don't discard it
        await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/no-discard",
            },
        )

        # Get discarded content
        response = await authenticated_client.get("/api/v1/content/discarded")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0


class TestStatsEndpoint:
    """Tests for GET /stats endpoint."""

    async def test_stats_endpoint(self, authenticated_client):
        """Test accurate statistics counts."""
        # Create 10 content items
        content_ids = []
        for i in range(10):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/stats-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Keep 4 items
        for i in range(4):
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_ids[i], "action": "keep"},
            )

        # Discard 3 items
        for i in range(4, 7):
            await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": content_ids[i], "action": "discard"},
            )

        # Get stats
        response = await authenticated_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify counts: 10 total, 4 kept, 3 discarded, 3 pending
        assert data["kept"] == 4
        assert data["discarded"] == 3
        assert data["pending"] == 3  # 10 - 4 - 3 = 3

    async def test_stats_empty(self, authenticated_client):
        """Test stats with no content."""
        response = await authenticated_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 0
        assert data["kept"] == 0
        assert data["discarded"] == 0


class TestSwipeMutualExclusivity:
    """Tests for edge cases and mutual exclusivity."""

    async def test_kept_and_discarded_mutually_exclusive(self, authenticated_client):
        """Test that same content cannot be both kept and discarded."""
        # Create content
        response = await authenticated_client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/mutual-exclude",
            },
        )
        content_id = response.json()["id"]

        # Keep the content
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get kept and verify content is there
        kept_response = await authenticated_client.get("/api/v1/content/kept")
        kept_ids = [c["id"] for c in kept_response.json()["items"]]
        assert content_id in kept_ids

        # Get discarded and verify content is NOT there
        discarded_response = await authenticated_client.get("/api/v1/content/discarded")
        discarded_ids = [c["id"] for c in discarded_response.json()["items"]]
        assert content_id not in discarded_ids

    async def test_pending_excludes_kept_and_discarded(self, authenticated_client):
        """Test that pending content excludes all swiped items."""
        # Create 3 content items
        content_ids = []
        for i in range(3):
            response = await authenticated_client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/pending-exclude-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Keep item 0, discard item 1, leave item 2 pending
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_ids[0], "action": "keep"},
        )
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_ids[1], "action": "discard"},
        )

        # Get pending - should only return item 2
        response = await authenticated_client.get("/api/v1/content/pending")
        data = response.json()

        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == content_ids[2]
