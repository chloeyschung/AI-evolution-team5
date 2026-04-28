"""TDD tests asserting all auth.py datetime fields use Z-suffix (ISO 8601 iOS-compatible).

These tests assert that every datetime field returned by auth endpoints ends with "Z",
not "+00:00". They are written BEFORE the fix and should FAIL initially.
"""

from datetime import timedelta
from unittest.mock import patch, AsyncMock

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user
from src.auth.tokens import create_access_token, create_refresh_token
from src.utils.datetime_utils import utc_now
from src.utils.token_hashing import hash_access_token
from src.data.models import AuthenticationToken, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Z_SUFFIX_MSG = "datetime field must end with 'Z' (iOS-compatible UTC suffix)"


def assert_z_suffix(value: str, field: str) -> None:
    assert isinstance(value, str), f"{field}: expected str, got {type(value)}"
    assert value.endswith("Z"), f"{field}: got {value!r} — {Z_SUFFIX_MSG}"


# ---------------------------------------------------------------------------
# 1. GET /auth/status  →  token_expires_at  (line ~112)
# ---------------------------------------------------------------------------


async def test_auth_status_token_expires_at_has_z_suffix(async_client, db):
    """token_expires_at in GET /auth/status must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="status@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()

        access_token = create_access_token(user.id)
        token = AuthenticationToken(
            user_id=user.id,
            access_token=hash_access_token(access_token),
            refresh_token=hash_access_token(create_refresh_token()),
            expires_at=utc_now() + timedelta(hours=1),
        )
        session.add(token)
        await session.commit()

    resp = await async_client.get(
        "/api/v1/auth/status",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert data["is_authenticated"] is True
    assert_z_suffix(data["token_expires_at"], "token_expires_at")


# ---------------------------------------------------------------------------
# 2. POST /auth/refresh  →  expires_at  (line ~160)
# ---------------------------------------------------------------------------


async def test_token_refresh_expires_at_has_z_suffix(async_client, db):
    """expires_at in POST /auth/refresh response must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="refresh@example.com", password="SecurePass123!")

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "SecurePass123!"},
    )
    assert login_resp.status_code == 200, login_resp.json()
    refresh_token = login_resp.json()["refresh_token"]

    resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert_z_suffix(data["expires_at"], "expires_at")


# ---------------------------------------------------------------------------
# 3. POST /auth/login  →  expires_at  (line ~589)
# ---------------------------------------------------------------------------


async def test_email_login_expires_at_has_z_suffix(async_client, db):
    """expires_at in POST /auth/login response must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="login@example.com", password="SecurePass123!")

    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert_z_suffix(data["expires_at"], "expires_at")


# ---------------------------------------------------------------------------
# 4. POST /auth/google  →  expires_at, user.created_at, user.updated_at
#    (lines ~270, 277, 278)
# ---------------------------------------------------------------------------


async def test_google_login_datetime_fields_have_z_suffix(async_client, db):
    """expires_at, user.created_at, user.updated_at in POST /auth/google must end with Z."""
    fake_token_info = {
        "sub": "google-sub-dt-001",
        "email": "google-dt@example.com",
        "name": "Google DT User",
        "picture": None,
        "email_verified": True,
        "aud": "test_google_client_id_for_local_development",
    }
    with patch("src.auth.google_oauth.verify_google_id_token", return_value=fake_token_info):
        resp = await async_client.post(
            "/api/v1/auth/google",
            json={
                "google_id_token": "fake-id-token",
                "google_user_info": {
                    "id": "google-sub-dt-001",
                    "email": "google-dt@example.com",
                    "name": "Google DT User",
                    "picture": None,
                },
            },
        )

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert_z_suffix(data["expires_at"], "expires_at")
    assert_z_suffix(data["user"]["created_at"], "user.created_at")
    assert_z_suffix(data["user"]["updated_at"], "user.updated_at")


# ---------------------------------------------------------------------------
# 5. POST /auth/google/code  →  expires_at, user.created_at, user.updated_at
#    (lines ~408, 415, 416)
# ---------------------------------------------------------------------------


async def test_google_code_login_datetime_fields_have_z_suffix(async_client, db):
    """expires_at, user.created_at, user.updated_at in POST /auth/google/code must end with Z."""
    fake_user_info = {
        "sub": "google-sub-code-dt-001",
        "email": "google-code-dt@example.com",
        "name": "Google Code DT User",
        "picture": None,
        "email_verified": True,
    }
    with patch(
        "src.auth.google_oauth.exchange_auth_code_for_tokens",
        return_value=("fake-id-token", fake_user_info),
    ):
        resp = await async_client.post(
            "/api/v1/auth/google/code",
            json={
                "code": "fake-auth-code",
            },
        )

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert_z_suffix(data["expires_at"], "expires_at")
    assert_z_suffix(data["user"]["created_at"], "user.created_at")
    assert_z_suffix(data["user"]["updated_at"], "user.updated_at")
