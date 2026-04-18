"""Tests for unified APIError schema and HTTPException handler (Task 10).

TDD: these tests are written BEFORE the implementation.
They assert the unified error shape:
  {"error": str, "message": str, "code": int, "details": dict | None}
"""
import pytest

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user, make_unverified_user


# ---------------------------------------------------------------------------
# Tests — pure shape (no DB needed; use async_client which brings in db)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_http_exception_returns_unified_error_shape(async_client):
    """HTTPException(401) must return {error, message, code, details} — not {detail}."""
    # /api/v1/content requires auth; triggers 401 HTTPException
    response = await async_client.get("/api/v1/content")
    assert response.status_code == 401
    body = response.json()
    # Must have the unified keys
    assert "error" in body, f"missing 'error' key, got: {body}"
    assert "message" in body, f"missing 'message' key, got: {body}"
    assert "code" in body, f"missing 'code' key, got: {body}"
    # Must NOT use the old FastAPI default key
    assert "detail" not in body, f"'detail' key still present, got: {body}"
    # code must match HTTP status
    assert body["code"] == 401


@pytest.mark.asyncio
async def test_http_exception_404_returns_unified_error_shape(async_client):
    """A 404 or 401 HTTPException must return the unified shape."""
    response = await async_client.get("/api/v1/content/999999")
    # Either 401 (unauthenticated) or 404 — both should use unified shape
    assert response.status_code in (401, 404)
    body = response.json()
    assert "error" in body
    assert "message" in body
    assert "code" in body
    assert "detail" not in body


@pytest.mark.asyncio
async def test_http_exception_with_dict_detail_maps_to_unified_shape(async_client, db):
    """When HTTPException.detail is a dict with error/message keys,
    they must be promoted to top-level error/message with extras in details."""
    # The register endpoint raises 409 with a dict detail like:
    # {"error": "email_exists", "providers": ["email_password"]}
    # After the handler it should be:
    # {"error": "email_exists", "message": ..., "code": 409, "details": {"providers": [...]}}
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="conflict@example.com", password="Pass1!")

    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "conflict@example.com", "password": "pass2"},
    )
    assert response.status_code == 409
    body = response.json()
    assert "error" in body
    assert body["error"] == "email_exists"
    assert "message" in body
    assert "code" in body
    assert body["code"] == 409
    assert "detail" not in body
    # providers should be in details
    assert body.get("details", {}).get("providers") is not None


@pytest.mark.asyncio
async def test_http_exception_with_dict_detail_email_not_verified(async_client, db):
    """dict detail with error+message+extra fields maps correctly."""
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="unverified2@example.com", password="Pass1!")

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "unverified2@example.com", "password": "Pass1!"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "email_not_verified"
    assert "message" in body
    assert body["code"] == 403
    assert "detail" not in body
    # can_resend is an extra field → goes into details
    assert body.get("details", {}).get("can_resend") is True


@pytest.mark.asyncio
async def test_code_field_matches_http_status_for_string_detail(async_client):
    """When detail is a plain string, code must equal the HTTP status."""
    response = await async_client.delete("/api/v1/content/999")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert isinstance(body["error"], str)
    assert isinstance(body["message"], str)
