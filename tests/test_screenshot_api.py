"""Tests for POST /api/v1/screenshot endpoint."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_jpeg_bytes() -> bytes:
    """Return a minimal valid JPEG header + trailer."""
    # SOI + minimal JFIF APP0 marker + EOI
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\xff\xd9"
    )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


@pytest.fixture
def mock_image_processor():
    """Patch ImageProcessor.process_bytes to avoid R2/Modal calls in tests."""
    from src.ai.metadata_extractor import ContentMetadata
    from src.constants import ContentType

    fake_metadata = ContentMetadata(
        platform="screenshot",
        content_type=ContentType.IMAGE,
        url="",
        summary="Extracted OCR text",
        thumbnail_url="https://r2.example.com/thumb.jpg",
        ocr_text="Extracted OCR text",
        linked_url="https://example.com",
        preview_url="https://r2.example.com/preview.jpg",
    )
    with patch(
        "src.api.routers.screenshot.ImageProcessor.process_bytes",
        new_callable=AsyncMock,
        return_value=fake_metadata,
    ) as mock:
        yield mock


async def test_screenshot_upload_returns_201(
    authenticated_client: AsyncClient,
    mock_image_processor,
):
    """POST /screenshot with valid base64 image returns 201 + ContentResponse."""
    jpeg = _make_jpeg_bytes()
    resp = await authenticated_client.post(
        "/api/v1/screenshot",
        json={
            "image_base64": _b64(jpeg),
            "original_format": "jpeg",
            "width": 1280,
            "height": 720,
        },
        headers={"Idempotency-Key": "test-key-001"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["content_type"] == "image"
    assert body["thumbnail_url"] is not None
    assert body["linked_url"] == "https://example.com"
    assert body["id"] > 0


async def test_screenshot_idempotency_replay_returns_same_id(
    authenticated_client: AsyncClient,
    mock_image_processor,
):
    """Replaying the same Idempotency-Key returns the same content_id."""
    jpeg = _make_jpeg_bytes()
    payload = {
        "image_base64": _b64(jpeg),
        "original_format": "jpeg",
        "width": 800,
        "height": 600,
    }
    headers = {"Idempotency-Key": "test-key-idempotency-002"}

    r1 = await authenticated_client.post("/api/v1/screenshot", json=payload, headers=headers)
    r2 = await authenticated_client.post("/api/v1/screenshot", json=payload, headers=headers)

    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["id"] == r2.json()["id"], "Idempotent replay must return same content_id"
    # Processor should only be called once (second call hit cache)
    assert mock_image_processor.call_count == 1


async def test_screenshot_requires_idempotency_key(authenticated_client: AsyncClient):
    """Missing Idempotency-Key header → 400."""
    resp = await authenticated_client.post(
        "/api/v1/screenshot",
        json={
            "image_base64": _b64(_make_jpeg_bytes()),
            "original_format": "jpeg",
            "width": 800,
            "height": 600,
        },
    )
    assert resp.status_code == 400


async def test_screenshot_rejects_invalid_base64(authenticated_client: AsyncClient):
    """Non-base64 image_base64 → 400."""
    resp = await authenticated_client.post(
        "/api/v1/screenshot",
        json={
            "image_base64": "not-valid-base64!!!",
            "original_format": "jpeg",
            "width": 800,
            "height": 600,
        },
        headers={"Idempotency-Key": "test-invalid-003"},
    )
    assert resp.status_code == 400


async def test_screenshot_requires_auth(async_client: AsyncClient):
    """Unauthenticated request → 401."""
    resp = await async_client.post(
        "/api/v1/screenshot",
        json={
            "image_base64": _b64(_make_jpeg_bytes()),
            "original_format": "jpeg",
            "width": 800,
            "height": 600,
        },
        headers={"Idempotency-Key": "test-noauth-004"},
    )
    assert resp.status_code == 401


async def test_screenshot_cross_user_content_not_visible(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    mock_image_processor,
):
    """Content created by one user is not accessible via another user's token."""
    from datetime import timedelta

    import httpx
    from httpx import ASGITransport

    from src.api.app import app
    from src.auth.tokens import create_access_token, create_refresh_token
    from src.data.models import AuthenticationToken, UserAuthMethod, UserProfile
    from src.constants import AuthProvider
    from src.utils.datetime_utils import utc_now
    from src.utils.token_hashing import hash_access_token

    # Create a second user
    user2 = UserProfile(email="user2@example.com", display_name=None, created_at=utc_now(), updated_at=utc_now())
    db_session.add(user2)
    await db_session.flush()

    auth_method2 = UserAuthMethod(
        user_id=user2.id, provider=AuthProvider.GOOGLE, provider_id="google_sub_user2", email_verified=True, verified_at=utc_now()
    )
    db_session.add(auth_method2)

    token2 = create_access_token(user2.id)
    auth_token2 = AuthenticationToken(
        user_id=user2.id,
        access_token=hash_access_token(token2),
        refresh_token=hash_access_token(create_refresh_token()),
        expires_at=utc_now() + timedelta(hours=1),
    )
    db_session.add(auth_token2)
    await db_session.commit()

    # User 1 uploads a screenshot
    jpeg = _make_jpeg_bytes()
    r1 = await authenticated_client.post(
        "/api/v1/screenshot",
        json={"image_base64": _b64(jpeg), "original_format": "jpeg", "width": 800, "height": 600},
        headers={"Idempotency-Key": "cross-user-test-005"},
    )
    assert r1.status_code == 201
    content_id = r1.json()["id"]

    # User 2 tries to GET that content
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token2}"},
    ) as client2:
        r2 = await client2.get(f"/api/v1/content/{content_id}")
        assert r2.status_code == 404, f"Cross-user access should return 404, got {r2.status_code}"
