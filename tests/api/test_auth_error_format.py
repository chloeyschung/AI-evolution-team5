"""Tests for consistent APIError format in auth.py error responses (Task 11).

Each error path must return:
  {"error": str, "message": str, "code": int, "details": dict | None}

The 'message' field must be a human-readable string — not a stringified dict
like "{'error': 'invalid_credentials'}", which is what the Task 10 handler
produces when a dict detail lacks a 'message' key.
"""
import pytest
from unittest.mock import patch

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user, make_unverified_user


def _assert_api_error_shape(body: dict, expected_error: str | None = None) -> None:
    """Assert unified APIError shape with a human-readable message.

    Checks:
    - 'error' and 'message' keys are present and are plain strings
    - 'detail' key is absent (old FastAPI default)
    - 'message' is NOT a stringified dict (e.g. "{'error': 'x'}")
    """
    assert "error" in body, f"missing 'error' key: {body}"
    assert "message" in body, f"missing 'message' key: {body}"
    assert isinstance(body["error"], str), f"'error' is not str: {body}"
    assert isinstance(body["message"], str), f"'message' is not str: {body}"
    assert "detail" not in body, f"'detail' key still present: {body}"
    # message must not be a raw stringified dict
    msg = body["message"]
    assert not (msg.startswith("{") and msg.endswith("}")), (
        f"'message' is a stringified dict, expected human text: {msg!r}"
    )
    if expected_error is not None:
        assert body["error"] == expected_error, (
            f"expected error={expected_error!r}, got {body['error']!r}"
        )


# ---------------------------------------------------------------------------
# /auth/refresh — was: ErrorCode enum as detail (StrEnum, but no 'message' key)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_invalid_token_has_human_message(async_client):
    """POST /auth/refresh with bad token: error+message must be human-readable strings."""
    resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "notavalidtoken"},
    )
    assert resp.status_code == 401
    _assert_api_error_shape(resp.json(), expected_error="invalid_refresh_token")


# ---------------------------------------------------------------------------
# /auth/google — was: f-string detail like "invalid_google_token: <exc msg>"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_login_invalid_token_has_human_message(async_client):
    """POST /auth/google with rejected Google token must have separate error + message."""
    from src.auth.google_oauth import GoogleTokenVerificationError

    with patch("src.auth.google_oauth.verify_google_id_token",
               side_effect=GoogleTokenVerificationError("bad token")):
        resp = await async_client.post(
            "/api/v1/auth/google",
            json={
                "google_id_token": "fake",
                "google_user_info": {
                    "id": "sub123",
                    "email": "user@example.com",
                    "name": "Test User",
                    "picture": None,
                },
            },
        )
    assert resp.status_code == 401
    body = resp.json()
    _assert_api_error_shape(body, expected_error="invalid_google_token")
    # message must NOT contain the error code (it was an f-string before)
    assert body["message"] != body["error"], (
        "message should be human text, not a copy of the error code"
    )


# ---------------------------------------------------------------------------
# /auth/google/code — was: plain string "OAuth code is required"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_code_missing_code_has_human_message(async_client):
    """POST /auth/google/code with empty code: must return unified shape."""
    resp = await async_client.post(
        "/api/v1/auth/google/code",
        json={"code": ""},
    )
    assert resp.status_code == 400
    _assert_api_error_shape(resp.json())


# ---------------------------------------------------------------------------
# /auth/google/code — was: f-string "invalid_google_token: <exc msg>"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_code_exchange_failure_has_human_message(async_client):
    """POST /auth/google/code with exchange failure: error code and message are separate."""
    from src.auth.google_oauth import GoogleTokenVerificationError

    with patch("src.auth.google_oauth.exchange_auth_code_for_tokens",
               side_effect=GoogleTokenVerificationError("exchange failed")):
        resp = await async_client.post(
            "/api/v1/auth/google/code",
            json={"code": "some-valid-looking-code"},
        )
    assert resp.status_code == 401
    body = resp.json()
    _assert_api_error_shape(body, expected_error="invalid_google_token")
    assert body["message"] != body["error"]


# ---------------------------------------------------------------------------
# /auth/google/code — was: plain string "Missing email or user ID from Google"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_code_missing_user_info_has_human_message(async_client):
    """POST /auth/google/code when Google returns no email/sub: unified shape."""
    with patch("src.auth.google_oauth.exchange_auth_code_for_tokens",
               return_value=("fake_id_token", {})):
        resp = await async_client.post(
            "/api/v1/auth/google/code",
            json={"code": "some-code"},
        )
    assert resp.status_code == 401
    _assert_api_error_shape(resp.json())


# ---------------------------------------------------------------------------
# /auth/verify-email — was: {"error": "invalid_or_expired_token"} — no message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_invalid_token_has_human_message(async_client):
    """POST /auth/verify-email invalid token: message must be human text, not dict repr."""
    resp = await async_client.post("/api/v1/auth/verify-email", json={"token": "badtoken"})
    assert resp.status_code == 400
    _assert_api_error_shape(resp.json(), expected_error="invalid_or_expired_token")


# ---------------------------------------------------------------------------
# /auth/login — was: {"error": "invalid_credentials"} — no message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_unknown_user_has_human_message(async_client):
    """POST /auth/login unknown email: message must be human text, not dict repr."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "anything"},
    )
    assert resp.status_code == 401
    _assert_api_error_shape(resp.json(), expected_error="invalid_credentials")


@pytest.mark.asyncio
async def test_login_wrong_password_has_human_message(async_client, db):
    """POST /auth/login wrong password: message must be human text, not dict repr."""
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="login-wrong-pw@example.com", password="RealPass1!")

    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login-wrong-pw@example.com", "password": "WrongPass1!"},
    )
    assert resp.status_code == 401
    _assert_api_error_shape(resp.json(), expected_error="invalid_credentials")


# ---------------------------------------------------------------------------
# /auth/password-reset/confirm — was: {"error": "invalid_or_expired_token"} — no message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_password_reset_confirm_invalid_token_has_human_message(async_client):
    """POST /auth/password-reset/confirm bad token: message must be human text."""
    resp = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "bogustoken", "new_password": "NewPass2!"},
    )
    assert resp.status_code == 400
    _assert_api_error_shape(resp.json(), expected_error="invalid_or_expired_token")


# ---------------------------------------------------------------------------
# /auth/link-account — was: {"error": "email_taken_by_another_account"} — no message
#                       and: {"error": "already_linked"} — no message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_link_account_email_taken_has_human_message(async_client, db):
    """POST /auth/link-account email owned by another user: message must be human text."""
    async with AsyncTestingSessionLocal() as session:
        _user_a, _token_a = await make_user(session, email="link-owner-a@example.com", password="PassA1!")
        _user_b, token_b = await make_user(session, email="link-owner-b@example.com", password="PassB1!")

    resp = await async_client.post(
        "/api/v1/auth/link-account",
        json={"email": "link-owner-a@example.com", "password": "anything"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 409
    _assert_api_error_shape(resp.json(), expected_error="email_taken_by_another_account")


@pytest.mark.asyncio
async def test_link_account_already_linked_has_human_message(async_client, db):
    """POST /auth/link-account already linked email: message must be human text."""
    async with AsyncTestingSessionLocal() as session:
        _user, token = await make_user(session, email="link-already@example.com", password="Pass1!")

    resp = await async_client.post(
        "/api/v1/auth/link-account",
        json={"email": "link-already@example.com", "password": "anything"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    _assert_api_error_shape(resp.json(), expected_error="already_linked")
