"""Tests for iOS retry idempotency on SwipeHistory (user_id, content_id) unique constraint.

Scenario: iOS retries a swipe POST after a network timeout. Without the unique constraint,
a second insert creates a duplicate row — silently corrupting data. With the constraint,
the second call must:
  - Return 200 or 201 (not a 500/409 error)
  - Return the existing record
  - Leave exactly ONE SwipeHistory row for (user_id, content_id) in the DB
"""

import pytest
from sqlalchemy import select, func

from src.data.models import SwipeHistory
from tests.conftest import AsyncTestingSessionLocal


class TestSwipeIdempotency:
    """Duplicate-swipe (iOS retry) idempotency tests."""

    async def test_duplicate_single_swipe_returns_200(self, authenticated_client):
        """Second POST /swipe for same (user, content) must return 200 or 201, not 5xx."""
        # Create content
        resp = await authenticated_client.post(
            "/api/v1/content",
            json={"platform": "Test", "content_type": "article", "url": "https://example.com/idem-1"},
        )
        assert resp.status_code == 201, resp.text
        content_id = resp.json()["id"]

        # First swipe — normal path
        r1 = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )
        assert r1.status_code in (200, 201), f"First swipe failed: {r1.text}"

        # Second swipe — iOS retry scenario
        r2 = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )
        assert r2.status_code in (200, 201), (
            f"Second (retry) swipe returned {r2.status_code}: {r2.text}. "
            "Expected idempotent 200/201."
        )

    async def test_duplicate_single_swipe_returns_same_record(self, authenticated_client):
        """Second POST /swipe for same (user, content) must return the original record."""
        resp = await authenticated_client.post(
            "/api/v1/content",
            json={"platform": "Test", "content_type": "article", "url": "https://example.com/idem-2"},
        )
        content_id = resp.json()["id"]

        r1 = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )
        first_id = r1.json()["id"]

        r2 = await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )
        second_id = r2.json()["id"]

        assert first_id == second_id, (
            f"Retry returned a different record ID ({second_id} != {first_id}). "
            "This means a duplicate row was created."
        )

    async def test_duplicate_single_swipe_creates_only_one_db_row(self, authenticated_client):
        """After two identical swipe POSTs, exactly one SwipeHistory row must exist in DB."""
        resp = await authenticated_client.post(
            "/api/v1/content",
            json={"platform": "Test", "content_type": "article", "url": "https://example.com/idem-3"},
        )
        content_id = resp.json()["id"]

        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )
        await authenticated_client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        async with AsyncTestingSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(SwipeHistory)
                    .where(SwipeHistory.content_id == content_id)
                )
            ).scalar()

        assert count == 1, (
            f"Expected exactly 1 SwipeHistory row, found {count}. "
            "Duplicate rows were inserted on retry."
        )

    async def test_non_duplicate_swipes_still_work(self, authenticated_client):
        """Swipes on different content items must still all be recorded (no regression)."""
        content_ids = []
        for i in range(3):
            resp = await authenticated_client.post(
                "/api/v1/content",
                json={"platform": "Test", "content_type": "article", "url": f"https://example.com/idem-nd-{i}"},
            )
            content_ids.append(resp.json()["id"])

        for cid in content_ids:
            r = await authenticated_client.post(
                "/api/v1/swipe",
                json={"content_id": cid, "action": "keep"},
            )
            assert r.status_code in (200, 201), f"Swipe on content {cid} failed: {r.text}"

        async with AsyncTestingSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(SwipeHistory)
                    .where(SwipeHistory.content_id.in_(content_ids))
                )
            ).scalar()

        assert count == 3, f"Expected 3 distinct SwipeHistory rows, got {count}"
