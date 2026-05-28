"""Tests for reading statistics endpoint."""


class TestStatsEndpoint:
    async def test_stats_empty(self, authenticated_client):
        """Stats returns zero counts when user has no swipes."""
        response = await authenticated_client.get("/api/v1/swipe-stats")
        assert response.status_code == 200
        data = response.json()
        assert data["kept"] == 0
        assert data["deleted"] == 0
        assert data["skipped"] == 0
        assert data["total"] == 0

    async def test_stats_after_swipes(self, authenticated_client):
        """Stats reflects actual swipe history."""
        for i in range(3):
            r = await authenticated_client.post(
                "/api/v1/content",
                json={"platform": "Test", "content_type": "article", "url": f"https://stats-test.com/{i}"},
            )
            content_id = r.json()["id"]
            action = "keep" if i < 2 else "discard"
            await authenticated_client.post(
                "/api/v1/swipe/batch",
                json={"actions": [{"content_id": content_id, "action": action}]},
            )

        response = await authenticated_client.get("/api/v1/swipe-stats")
        assert response.status_code == 200
        data = response.json()
        assert data["kept"] == 2
        assert data["deleted"] == 1
        assert data["total"] == 3
