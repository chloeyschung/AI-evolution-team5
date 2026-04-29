"""Tests for DAT-003: Soft Delete & Data Recovery.

Covers:
- Soft delete sets is_deleted flag + deleted_at timestamp
- Soft delete is idempotent (second call returns 200)
- Deleted content is excluded from list / get queries
- Restore within window succeeds (→ ContentResponse)
- Restore after 30-day window returns 410
- Account cascade soft-deletes owned Content and InterestTag rows
- deleted_at and recoverable_until use Z-suffix (iOS-compatible ISO 8601)
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Content, InterestTag, UserProfile
from src.utils.datetime_utils import utc_now

# ---------------------------------------------------------------------------
# Z-suffix helpers (iOS-compatible datetime format)
# ---------------------------------------------------------------------------

Z_SUFFIX_MSG = "datetime field must end with 'Z' (iOS-compatible UTC suffix)"


def assert_z_suffix(value: str, field: str) -> None:
    assert isinstance(value, str), f"{field}: expected str, got {type(value)}"
    assert value.endswith("Z"), f"{field}: got {value!r} — {Z_SUFFIX_MSG}"

def _naive_utc_now():
    """Return current UTC time as naive datetime (matches SQLite storage format)."""
    return utc_now().replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_content(authenticated_client: AsyncClient, url: str = "https://example.com/article") -> dict:
    """Create a content item and return the response JSON."""
    resp = await authenticated_client.post(
        "/api/v1/content",
        json={
            "platform": "web",
            "content_type": "article",
            "url": url,
            "title": "Test Article",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Soft delete — basic behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_returns_200_with_recoverable_until(authenticated_client: AsyncClient):
    """DELETE /content/{id} returns 200 with is_deleted=True and recoverable_until."""
    content = await _create_content(authenticated_client)
    resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == content["id"]
    assert body["is_deleted"] is True
    assert "deleted_at" in body
    assert "recoverable_until" in body


@pytest.mark.asyncio
async def test_soft_delete_sets_flag_in_db(authenticated_client: AsyncClient, db_session: AsyncSession):
    """Verify is_deleted and deleted_at are persisted to DB after soft delete."""
    content = await _create_content(authenticated_client, url="https://example.com/db-check")
    content_id = content["id"]

    resp = await authenticated_client.delete(f"/api/v1/content/{content_id}")
    assert resp.status_code == 200

    # Re-fetch from DB (bypass soft-delete filter by querying directly)
    result = await db_session.execute(select(Content).where(Content.id == content_id))
    row = result.scalar_one_or_none()

    assert row is not None
    assert row.is_deleted is True
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_soft_delete_is_idempotent(authenticated_client: AsyncClient):
    """Second soft-delete call on the same content returns 200 (not 404)."""
    content = await _create_content(authenticated_client, url="https://example.com/idempotent")

    resp1 = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert resp1.status_code == 200

    resp2 = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# Deleted content excluded from list / get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_content_excluded_from_list(authenticated_client: AsyncClient):
    """Soft-deleted content does not appear in GET /content list."""
    content = await _create_content(authenticated_client, url="https://example.com/invisible")
    resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert resp.status_code == 200

    list_resp = await authenticated_client.get("/api/v1/content")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()["items"]]
    assert content["id"] not in ids


@pytest.mark.asyncio
async def test_deleted_content_returns_404_on_get(authenticated_client: AsyncClient):
    """GET /content/{id} for a soft-deleted item returns 404."""
    content = await _create_content(authenticated_client, url="https://example.com/gone-detail")
    resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert resp.status_code == 200

    detail_resp = await authenticated_client.get(f"/api/v1/content/{content['id']}")
    assert detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_trash_total_counts_all_matching_rows_not_page_length(authenticated_client: AsyncClient):
    """GET /content/trash total reports all deleted rows, not just current page size."""
    for index in range(3):
        content = await _create_content(
            authenticated_client,
            url=f"https://example.com/trash-total-{index}",
        )
        resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
        assert resp.status_code == 200

    page = await authenticated_client.get("/api/v1/content/trash?limit=2&offset=0")
    assert page.status_code == 200
    body = page.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["has_more"] is True
    assert body["next_offset"] == 2


# ---------------------------------------------------------------------------
# Restore — within window
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_within_window_returns_200(authenticated_client: AsyncClient):
    """POST /content/{id}/restore within 30 days returns 200 with is_deleted=False."""
    content = await _create_content(authenticated_client, url="https://example.com/restore-ok")
    del_resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert del_resp.status_code == 200

    restore_resp = await authenticated_client.post(f"/api/v1/content/{content['id']}/restore")
    assert restore_resp.status_code == 200, restore_resp.text

    body = restore_resp.json()
    assert body["id"] == content["id"]


@pytest.mark.asyncio
async def test_restore_makes_content_visible_again(authenticated_client: AsyncClient):
    """After restore, content reappears in the list."""
    content = await _create_content(authenticated_client, url="https://example.com/restore-visible")
    await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    await authenticated_client.post(f"/api/v1/content/{content['id']}/restore")

    list_resp = await authenticated_client.get("/api/v1/content")
    ids = [c["id"] for c in list_resp.json()["items"]]
    assert content["id"] in ids


# ---------------------------------------------------------------------------
# Restore — window expired (410)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_after_30_days_returns_410(authenticated_client: AsyncClient, db_session: AsyncSession):
    """POST /content/{id}/restore after recovery window returns 410 Gone."""
    content = await _create_content(authenticated_client, url="https://example.com/expired-restore")
    del_resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")
    assert del_resp.status_code == 200

    # Simulate 31-day-old deletion by back-dating deleted_at directly
    expired_at = _naive_utc_now() - timedelta(days=31)
    await db_session.execute(
        update(Content)
        .where(Content.id == content["id"])
        .values(deleted_at=expired_at)
    )
    await db_session.commit()

    restore_resp = await authenticated_client.post(f"/api/v1/content/{content['id']}/restore")
    assert restore_resp.status_code == 410
    assert restore_resp.json()["error"] == "recovery_window_expired"


@pytest.mark.asyncio
async def test_restore_within_29_days_succeeds(authenticated_client: AsyncClient, db_session: AsyncSession):
    """POST /content/{id}/restore at 29 days (within window) still returns 200."""
    content = await _create_content(authenticated_client, url="https://example.com/still-ok")
    await authenticated_client.delete(f"/api/v1/content/{content['id']}")

    # Back-date deleted_at to 29 days ago (still within window)
    recent_at = _naive_utc_now() - timedelta(days=29)
    await db_session.execute(
        update(Content)
        .where(Content.id == content["id"])
        .values(deleted_at=recent_at)
    )
    await db_session.commit()

    restore_resp = await authenticated_client.post(f"/api/v1/content/{content['id']}/restore")
    assert restore_resp.status_code == 200


# ---------------------------------------------------------------------------
# Account cascade soft-delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_delete_soft_deletes_content(
    authenticated_client: AsyncClient,
    test_user: int,
    db_session: AsyncSession,
):
    """Account deletion soft-deletes all owned Content rows."""
    # Create content first
    content = await _create_content(authenticated_client, url="https://example.com/cascade-content")
    content_id = content["id"]

    # Step 1: request deletion token
    resp1 = await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
    )
    assert resp1.status_code == 200
    token = resp1.json()["confirmation_token"]

    # Step 2: confirm deletion
    resp2 = await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True, "confirmation_token": token},
    )
    assert resp2.status_code == 200

    # Content row should now be soft-deleted
    result = await db_session.execute(select(Content).where(Content.id == content_id))
    row = result.scalar_one_or_none()
    assert row is not None, "Content row should not be hard-deleted"
    assert row.is_deleted is True
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_account_delete_soft_deletes_interest_tags(
    authenticated_client: AsyncClient,
    test_user: int,
    db_session: AsyncSession,
):
    """Account deletion soft-deletes all owned InterestTag rows."""
    # Add an interest tag
    tag_resp = await authenticated_client.post("/api/v1/interests", json={"tag": "python"})
    assert tag_resp.status_code in (200, 201)

    # Step 1: get deletion token
    resp1 = await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
    )
    assert resp1.status_code == 200
    token = resp1.json()["confirmation_token"]

    # Step 2: confirm deletion
    resp2 = await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True, "confirmation_token": token},
    )
    assert resp2.status_code == 200

    # InterestTag rows should be soft-deleted (not hard-deleted)
    result = await db_session.execute(
        select(InterestTag).where(InterestTag.user_id == test_user)
    )
    tags = result.scalars().all()
    assert all(t.is_deleted is True for t in tags), "All tags should be soft-deleted"


@pytest.mark.asyncio
async def test_account_delete_soft_deletes_user_profile(
    authenticated_client: AsyncClient,
    test_user: int,
    db_session: AsyncSession,
):
    """Account deletion sets is_deleted=True on the UserProfile."""
    resp1 = await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
    )
    token = resp1.json()["confirmation_token"]

    await authenticated_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True, "confirmation_token": token},
    )

    result = await db_session.execute(select(UserProfile).where(UserProfile.id == test_user))
    profile = result.scalar_one_or_none()
    assert profile is not None
    assert profile.is_deleted is True


# ---------------------------------------------------------------------------
# Z-suffix — DeletedContentResponse datetime fields (iOS API compliance)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_datetime_fields_have_z_suffix(authenticated_client: AsyncClient):
    """DELETE /content/{id} must return deleted_at and recoverable_until ending with Z.

    Pydantic's default datetime serialization emits '+00:00' instead of 'Z'.
    This test ensures DeletedContentResponse uses @field_serializer to produce
    iOS-compatible ISO 8601 strings ending with 'Z'.
    """
    content = await _create_content(authenticated_client, url="https://example.com/z-suffix-check")
    resp = await authenticated_client.delete(f"/api/v1/content/{content['id']}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_z_suffix(body["deleted_at"], "deleted_at")
    assert_z_suffix(body["recoverable_until"], "recoverable_until")
