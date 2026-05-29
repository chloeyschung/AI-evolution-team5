"""Integration tests for GET /stats/categories endpoint."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import ContentType
from src.data.models import Content, ContentStatus
from src.utils.datetime_utils import utc_now


async def _make_content(
    db_session: AsyncSession,
    user_id: int,
    url: str,
    auto_tag_category: str | None = None,
    status: ContentStatus = ContentStatus.INBOX,
) -> Content:
    c = Content(
        user_id=user_id,
        platform="web",
        content_type=ContentType.ARTICLE,
        url=url,
        title="Test Article",
        status=status,
        is_deleted=False,
        created_at=utc_now(),
        updated_at=utc_now(),
        auto_tag_category=auto_tag_category,
    )
    db_session.add(c)
    await db_session.commit()
    return c


class TestCategoryStatsEndpoint:
    """Tests for GET /stats/categories."""

    async def test_returns_200_with_empty_data(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/stats/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert data["categories"] == []

    async def test_counts_total_and_kept_per_category(
        self, authenticated_client, db_session, test_user
    ):
        await _make_content(db_session, test_user, "https://a.com/1", "Tech", ContentStatus.INBOX)
        await _make_content(db_session, test_user, "https://a.com/2", "Tech", ContentStatus.ARCHIVED)
        await _make_content(db_session, test_user, "https://a.com/3", "Tech", ContentStatus.ARCHIVED)
        await _make_content(db_session, test_user, "https://a.com/4", "Business", ContentStatus.INBOX)
        await _make_content(db_session, test_user, "https://a.com/5", "Business", ContentStatus.ARCHIVED)

        response = await authenticated_client.get("/api/v1/stats/categories")
        assert response.status_code == 200

        categories = {c["category"]: c for c in response.json()["categories"]}

        assert categories["Tech"]["total"] == 3
        assert categories["Tech"]["kept"] == 2
        assert categories["Business"]["total"] == 2
        assert categories["Business"]["kept"] == 1

    async def test_excludes_untagged_content(
        self, authenticated_client, db_session, test_user
    ):
        await _make_content(db_session, test_user, "https://b.com/1", "Tech", ContentStatus.ARCHIVED)
        await _make_content(db_session, test_user, "https://b.com/2", None, ContentStatus.ARCHIVED)

        response = await authenticated_client.get("/api/v1/stats/categories")
        assert response.status_code == 200

        categories = {c["category"]: c for c in response.json()["categories"]}
        assert "Tech" in categories
        assert len(categories) == 1

    async def test_excludes_deleted_content(
        self, authenticated_client, db_session, test_user
    ):
        await _make_content(db_session, test_user, "https://c.com/1", "Tech", ContentStatus.ARCHIVED)

        deleted = Content(
            user_id=test_user,
            platform="web",
            content_type=ContentType.ARTICLE,
            url="https://c.com/2",
            title="Deleted Article",
            status=ContentStatus.ARCHIVED,
            is_deleted=True,
            auto_tag_category="Tech",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(deleted)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/stats/categories")
        assert response.status_code == 200

        categories = {c["category"]: c for c in response.json()["categories"]}
        assert categories["Tech"]["total"] == 1

    async def test_scoped_to_authenticated_user(
        self, authenticated_client, db_session, test_user
    ):
        other_user_id = test_user + 9999

        await _make_content(db_session, test_user, "https://d.com/1", "Tech", ContentStatus.ARCHIVED)
        await _make_content(db_session, other_user_id, "https://d.com/2", "Tech", ContentStatus.ARCHIVED)
        await _make_content(db_session, other_user_id, "https://d.com/3", "Tech", ContentStatus.ARCHIVED)

        response = await authenticated_client.get("/api/v1/stats/categories")
        assert response.status_code == 200

        categories = {c["category"]: c for c in response.json()["categories"]}
        assert categories["Tech"]["total"] == 1
