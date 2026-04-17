"""API integration tests for email/password auth endpoints (AUTH-005)."""
from unittest.mock import patch

from sqlalchemy import select

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import (
    make_reset_token,
    make_unverified_user,
    make_user,
    make_verification_token,
)
from src.constants import AuthProvider
from src.data.models import PasswordResetToken, UserAuthMethod, UserProfile
from src.utils.datetime_utils import utc_now


async def test_register_creates_unverified_user(async_client, db):
    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "SecurePass123!"
        })
    assert resp.status_code == 201
    assert "verification" in resp.json()["message"].lower()


async def test_register_duplicate_email_returns_409(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="dup@example.com", password="Pass1!")

    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "dup@example.com", "password": "pass2"
    })
    assert resp.status_code == 409
    assert resp.json()["detail"] == {
        "error": "email_exists",
        "providers": ["email_password"],
    }


async def test_register_existing_email_with_google_provider_returns_409(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="multi-provider@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        session.add(UserAuthMethod(
            user_id=user.id,
            provider=AuthProvider.GOOGLE,
            provider_id="google-sub-123",
            email_verified=True,
            verified_at=utc_now(),
        ))
        await session.commit()

    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "multi-provider@example.com",
        "password": "Pass2!",
    })

    assert resp.status_code == 409
    assert resp.json()["detail"] == {
        "error": "email_exists",
        "providers": ["google"],
    }


async def test_register_existing_google_email_mixed_case_returns_409(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="MixedCase.Google@Example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        session.add(UserAuthMethod(
            user_id=user.id,
            provider=AuthProvider.GOOGLE,
            provider_id="google-sub-mixed-123",
            email_verified=True,
            verified_at=utc_now(),
        ))
        await session.commit()

    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "mixedcase.google@example.com",
        "password": "Pass2!",
    })

    assert resp.status_code == 409
    assert resp.json()["detail"] == {
        "error": "email_exists",
        "providers": ["google"],
    }


async def test_register_existing_unverified_rotates_token_and_returns_201(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, _ = await make_unverified_user(session, email="stuck@example.com", password="Pass1!")
        old_raw = await make_verification_token(session, user.id)

    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "stuck@example.com",
            "password": "AnotherPass2!"
        })

    assert resp.status_code == 201

    verify_old = await async_client.get(f"/api/v1/auth/verify-email?token={old_raw}")
    assert verify_old.status_code == 400


async def test_verify_email_valid_token(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, method = await make_unverified_user(session, email="verify@example.com")
        raw = await make_verification_token(session, user.id)

    resp = await async_client.get(f"/api/v1/auth/verify-email?token={raw}")
    assert resp.status_code == 200


async def test_verify_email_invalid_token_returns_400(async_client, db):
    resp = await async_client.get("/api/v1/auth/verify-email?token=badtoken")
    assert resp.status_code == 400


async def test_resend_verification_for_unverified_email_returns_200(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="resend@example.com", password="Pass1!")

    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/verify-email/resend", json={"email": "resend@example.com"})

    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower()


async def test_resend_verification_for_unknown_email_returns_same_200_message(async_client, db):
    resp = await async_client.post("/api/v1/auth/verify-email/resend", json={
        "email": "unknown@example.com",
    })

    assert resp.status_code == 200
    assert resp.json() == {
        "message": "If that email is registered and not yet verified, a verification email has been sent.",
    }


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


async def test_login_normalizes_mixed_case_whitespace_email(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email="login-normalized@example.com", password="GoodPass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "  Login-Normalized@Example.com  ",
        "password": "GoodPass1!"
    })

    assert resp.status_code == 200
    assert resp.json()["email"] == "login-normalized@example.com"


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
    assert detail == {
        "error": "email_not_verified",
        "can_resend": True,
        "message": "Email not verified. Please verify your email or request a new verification email.",
    }


# ── Password reset tests ──────────────────────────────────────────────────────

async def test_password_reset_request_returns_200(async_client, db):
    resp = await async_client.post("/api/v1/auth/password-reset/request", json={
        "email": "anyone@example.com"
    })
    assert resp.status_code == 200


async def test_password_reset_request_normalizes_mixed_case_whitespace_email(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, _ = await make_user(session, email="reset-normalized@example.com", password="OldPass1!")

    resp = await async_client.post("/api/v1/auth/password-reset/request", json={
        "email": "  Reset-Normalized@Example.com  "
    })

    assert resp.status_code == 200

    async with AsyncTestingSessionLocal() as session:
        result = await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        tokens = list(result.scalars().all())

    assert len(tokens) == 1


async def test_register_existing_unverified_updates_password_before_verification(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="update-password@example.com", password="OldPass1!")

    sent_tokens: list[str] = []

    def capture_verification_email(email: str, token: str) -> None:
        sent_tokens.append(token)

    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = capture_verification_email
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "update-password@example.com",
            "password": "NewPass2!"
        })

    assert resp.status_code == 201
    assert len(sent_tokens) == 1

    verify_resp = await async_client.get(f"/api/v1/auth/verify-email?token={sent_tokens[0]}")
    assert verify_resp.status_code == 200

    old_login = await async_client.post("/api/v1/auth/login", json={
        "email": "update-password@example.com",
        "password": "OldPass1!"
    })
    assert old_login.status_code == 401

    new_login = await async_client.post("/api/v1/auth/login", json={
        "email": "update-password@example.com",
        "password": "NewPass2!"
    })
    assert new_login.status_code == 200


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
