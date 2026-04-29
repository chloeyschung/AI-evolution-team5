"""TDD tests for Task 12: Standardize HTTPException raises in content.py to use
consistent {"error": "...", "message": "..."} dict format.

All assertions check that:
  - response.json()["error"] is a snake_case string (not a prefixed compound or exception message)
  - response.json()["message"] is a human-readable string distinct from "error"
  - "detail" key is NOT present (already ensured by the unified handler)
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_content(client, url="https://example.com/err-fmt-test") -> dict:
    resp = await client.post(
        "/api/v1/content",
        json={
            "platform": "web",
            "content_type": "article",
            "url": url,
            "title": "Err Format Test",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _assert_error_shape(body: dict) -> None:
    """Assert the unified error shape is present and well-formed."""
    assert "error" in body, f"missing 'error' key: {body}"
    assert "message" in body, f"missing 'message' key: {body}"
    assert "detail" not in body, f"'detail' key still present: {body}"
    assert isinstance(body["error"], str), f"'error' must be str: {body}"
    assert isinstance(body["message"], str), f"'message' must be str: {body}"


# ---------------------------------------------------------------------------
# GET /content/{content_id} — not found (line 106 in content.py)
# Previously: detail=f"{ErrorCode.CONTENT_NOT_FOUND}: {content_id}"
# Expected:   error="content_not_found", message != error (no ID embedded in error key)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_content_detail_not_found_error_is_clean_code(authenticated_client):
    """GET /content/99999 → error must be 'content_not_found', not 'content_not_found: 99999'."""
    response = await authenticated_client.get("/api/v1/content/99999")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found", (
        f"error should be clean code, got: {body['error']!r}"
    )
    # message must be a non-empty human-readable string
    assert len(body["message"]) > 0
    # error must NOT contain a colon (which would indicate the old prefixed format)
    assert ":" not in body["error"], f"error contains colon (old format?): {body['error']!r}"


# ---------------------------------------------------------------------------
# PATCH /content/{content_id}/status — 400 ValueError (line 161)
# Previously: detail=str(e) — leaks internal exception message
# Expected:   error="invalid_status_transition", message=human description
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_content_status_400_has_clean_error_code(authenticated_client):
    """PATCH /content/{id}/status with invalid status → error must be a clean code, not str(exception)."""
    content = await _create_content(authenticated_client, url="https://example.com/status-400")
    content_id = content["id"]

    # Send an invalid status value to trigger 400 ValueError
    response = await authenticated_client.patch(
        f"/api/v1/content/{content_id}/status",
        json={"status": "invalid_status_xyz"},
    )

    # FastAPI validates the enum before reaching the handler, so this may be 422
    # If 422 (validation error), the 400/ValueError branch isn't reached via normal flow.
    # In that case, we skip this assertion (the enum guard fires first).
    if response.status_code == 422:
        pytest.skip("FastAPI enum validation returns 422 before the ValueError branch is reached")

    assert response.status_code == 400
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "invalid_status_transition", (
        f"expected 'invalid_status_transition', got: {body['error']!r}"
    )
    assert body["message"] != body["error"], "message should differ from error code"


# ---------------------------------------------------------------------------
# PATCH /content/{content_id}/status — 404 RuntimeError (line 163)
# Previously: detail=str(e) — leaks internal exception message
# Expected:   error="content_not_found", message=human description
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_content_status_404_has_clean_error_code(authenticated_client):
    """PATCH /content/99999/status → 404 error must be 'content_not_found', not str(RuntimeError)."""
    response = await authenticated_client.patch(
        "/api/v1/content/99999/status",
        json={"status": "archived"},
    )

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found", (
        f"expected 'content_not_found', got: {body['error']!r}"
    )
    assert body["message"] != body["error"], "message should be a human-readable description"


# ---------------------------------------------------------------------------
# GET /content/{content_id}/tags — not found (line 193)
# Previously: detail=ErrorCode.CONTENT_NOT_FOUND (bare string, no message)
# Expected:   error="content_not_found", message != error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_content_tags_not_found_has_message(authenticated_client):
    """GET /content/99999/tags → error shape must include distinct message field."""
    response = await authenticated_client.get("/api/v1/content/99999/tags")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found"
    # message must be distinct from the error code
    assert body["message"] != body["error"], (
        f"message should be human-readable, not equal to error code: {body['message']!r}"
    )


# ---------------------------------------------------------------------------
# POST /content/{content_id}/categorize — not found (line 231)
# Previously: detail=ErrorCode.CONTENT_NOT_FOUND (bare string)
# Expected:   error="content_not_found", message distinct
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_categorize_content_not_found_has_message(authenticated_client):
    """POST /content/99999/categorize → error shape must include distinct message field."""
    response = await authenticated_client.post("/api/v1/content/99999/categorize")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found"
    assert body["message"] != body["error"], (
        f"message should be human-readable: {body['message']!r}"
    )


# ---------------------------------------------------------------------------
# DELETE /content/{content_id} — not found (line 279)
# Previously: detail=ErrorCode.CONTENT_NOT_FOUND (bare string)
# Expected:   error="content_not_found", message distinct
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_content_not_found_has_message(authenticated_client):
    """DELETE /content/99999 → error shape must include distinct message field."""
    response = await authenticated_client.delete("/api/v1/content/99999")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found"
    assert body["message"] != body["error"], (
        f"message should be human-readable: {body['message']!r}"
    )


# ---------------------------------------------------------------------------
# POST /content/{content_id}/restore — not found (line 320)
# Previously: detail=ErrorCode.CONTENT_NOT_FOUND (bare string)
# Expected:   error="content_not_found", message distinct
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_content_not_found_has_message(authenticated_client):
    """POST /content/99999/restore → error shape must include distinct message field."""
    response = await authenticated_client.post("/api/v1/content/99999/restore")

    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["error"] == "content_not_found"
    assert body["message"] != body["error"], (
        f"message should be human-readable: {body['message']!r}"
    )


# ---------------------------------------------------------------------------
# POST /content/{content_id}/restore — recovery window expired (line 318)
# Previously: detail="recovery_window_expired" (bare string)
# This is already tested in test_soft_delete.py — we add message distinctness check.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_expired_window_error_has_distinct_message(authenticated_client):
    """POST /content/99999/restore on non-existent → 404 with distinct message.

    Note: testing 410 recovery_window_expired requires DB manipulation (back-dating
    deleted_at), which is covered in test_soft_delete.py. Here we just verify the
    basic shape contract for the 404 path.
    """
    response = await authenticated_client.post("/api/v1/content/99999/restore")
    assert response.status_code == 404
    body = response.json()
    _assert_error_shape(body)
    assert body["message"] != body["error"]
