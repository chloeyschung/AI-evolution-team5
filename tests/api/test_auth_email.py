"""API integration tests for email/password auth endpoints (AUTH-005)."""
from unittest.mock import patch

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import (
    make_reset_token,
    make_unverified_user,
    make_user,
    make_verification_token,
)


async def test_register_creates_unverified_user(async_client, db):
    with patch("src.api.routes.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "SecurePass123!"
        })
    assert resp.status_code == 201
    assert "verification" in resp.json()["message"].lower()


async def test_register_duplicate_email_returns_409(async_client, db):
    with patch("src.api.routes.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        await async_client.post("/api/v1/auth/register", json={
            "email": "dup@example.com", "password": "pass1"
        })
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "dup@example.com", "password": "pass2"
        })
    assert resp.status_code == 409


async def test_verify_email_valid_token(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, method = await make_unverified_user(session, email="verify@example.com")
        raw = await make_verification_token(session, user.id)

    resp = await async_client.get(f"/api/v1/auth/verify-email?token={raw}")
    assert resp.status_code == 200


async def test_verify_email_invalid_token_returns_400(async_client, db):
    resp = await async_client.get("/api/v1/auth/verify-email?token=badtoken")
    assert resp.status_code == 400


# ── Login tests ───────────────────────────────────────────────────────────────

async def test_login_success(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="login@example.com", password="GoodPass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "GoodPass1!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user_id"] > 0
    assert data["email"] == "login@example.com"


async def test_login_wrong_password_returns_401(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="badpass@example.com", password="RealPass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "badpass@example.com",
        "password": "WrongPass1!"
    })
    assert resp.status_code == 401


async def test_login_unverified_email_returns_403(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="unverified@example.com", password="Pass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "unverified@example.com",
        "password": "Pass1!"
    })
    assert resp.status_code == 403


async def test_login_unverified_email_returns_403_with_resend_hint(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="unverified-hint@example.com", password="Pass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "unverified-hint@example.com",
        "password": "Pass1!"
    })

    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "email_not_verified"
    assert detail["can_resend"] is True


# ── Password reset tests ──────────────────────────────────────────────────────

async def test_password_reset_request_returns_200(async_client, db):
    resp = await async_client.post("/api/v1/auth/password-reset/request", json={
        "email": "anyone@example.com"
    })
    assert resp.status_code == 200


async def test_password_reset_confirm_valid(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, _ = await make_user(session, email="reset@example.com", password="OldPass1!")
        raw = await make_reset_token(session, user.id)

    resp = await async_client.post("/api/v1/auth/password-reset/confirm", json={
        "token": raw,
        "new_password": "NewPass2!"
    })
    assert resp.status_code == 200


async def test_password_reset_confirm_invalid_token_returns_400(async_client, db):
    resp = await async_client.post("/api/v1/auth/password-reset/confirm", json={
        "token": "bogus",
        "new_password": "NewPass2!"
    })
    assert resp.status_code == 400
