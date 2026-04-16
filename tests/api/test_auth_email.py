"""API integration tests for email/password auth endpoints (AUTH-005)."""
import pytest
from unittest.mock import patch


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
    from src.auth.email_auth import generate_token, hmac_email, hash_password, encrypt_email
    from src.data.email_auth_repository import EmailAuthRepository
    from src.data.models import UserProfile
    from tests.conftest import AsyncTestingSessionLocal
    from src.utils.datetime_utils import utc_now
    from datetime import timedelta
    from src.constants import AuthProvider

    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="verify@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        repo = EmailAuthRepository(session)
        await repo.create_auth_method(
            user.id, AuthProvider.EMAIL_PASSWORD,
            hmac_email("verify@example.com"),
            password_hash=hash_password("pass"),
            email_encrypted=encrypt_email("verify@example.com"),
        )
        raw, token_hash = generate_token()
        await repo.create_verification_token(user.id, token_hash, utc_now() + timedelta(hours=24))
        await session.commit()

    resp = await async_client.get(f"/api/v1/auth/verify-email?token={raw}")
    assert resp.status_code == 200


async def test_verify_email_invalid_token_returns_400(async_client, db):
    resp = await async_client.get("/api/v1/auth/verify-email?token=badtoken")
    assert resp.status_code == 400


# ── Login tests ───────────────────────────────────────────────────────────────

async def test_login_success(async_client, db):
    from src.auth.email_auth import hash_password, hmac_email, encrypt_email
    from src.data.email_auth_repository import EmailAuthRepository
    from src.data.models import UserProfile
    from tests.conftest import AsyncTestingSessionLocal
    from src.utils.datetime_utils import utc_now
    from src.constants import AuthProvider

    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="login@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        repo = EmailAuthRepository(session)
        method = await repo.create_auth_method(
            user.id, AuthProvider.EMAIL_PASSWORD,
            hmac_email("login@example.com"),
            password_hash=hash_password("GoodPass1!"),
            email_encrypted=encrypt_email("login@example.com"),
        )
        await repo.mark_email_verified(method.id)
        await session.commit()

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "GoodPass1!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password_returns_401(async_client, db):
    from src.auth.email_auth import hash_password, hmac_email, encrypt_email
    from src.data.email_auth_repository import EmailAuthRepository
    from src.data.models import UserProfile
    from tests.conftest import AsyncTestingSessionLocal
    from src.utils.datetime_utils import utc_now
    from src.constants import AuthProvider

    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="badpass@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        repo = EmailAuthRepository(session)
        method = await repo.create_auth_method(
            user.id, AuthProvider.EMAIL_PASSWORD,
            hmac_email("badpass@example.com"),
            password_hash=hash_password("RealPass1!"),
            email_encrypted=encrypt_email("badpass@example.com"),
        )
        await repo.mark_email_verified(method.id)
        await session.commit()

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "badpass@example.com",
        "password": "WrongPass1!"
    })
    assert resp.status_code == 401


async def test_login_unverified_email_returns_403(async_client, db):
    from src.auth.email_auth import hash_password, hmac_email, encrypt_email
    from src.data.email_auth_repository import EmailAuthRepository
    from src.data.models import UserProfile
    from tests.conftest import AsyncTestingSessionLocal
    from src.utils.datetime_utils import utc_now
    from src.constants import AuthProvider

    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="unverified@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        repo = EmailAuthRepository(session)
        await repo.create_auth_method(
            user.id, AuthProvider.EMAIL_PASSWORD,
            hmac_email("unverified@example.com"),
            password_hash=hash_password("Pass1!"),
            email_encrypted=encrypt_email("unverified@example.com"),
        )
        # NOT calling mark_email_verified
        await session.commit()

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "unverified@example.com",
        "password": "Pass1!"
    })
    assert resp.status_code == 403


# ── Password reset tests ──────────────────────────────────────────────────────

async def test_password_reset_request_returns_200(async_client, db):
    # Always returns 200 (no email enumeration)
    resp = await async_client.post("/api/v1/auth/password-reset/request", json={
        "email": "anyone@example.com"
    })
    assert resp.status_code == 200


async def test_password_reset_confirm_valid(async_client, db):
    from src.auth.email_auth import hash_password, hmac_email, encrypt_email, generate_token
    from src.data.email_auth_repository import EmailAuthRepository
    from src.data.models import UserProfile
    from tests.conftest import AsyncTestingSessionLocal
    from src.utils.datetime_utils import utc_now
    from datetime import timedelta
    from src.constants import AuthProvider

    async with AsyncTestingSessionLocal() as session:
        user = UserProfile(email="reset@example.com", created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
        repo = EmailAuthRepository(session)
        method = await repo.create_auth_method(
            user.id, AuthProvider.EMAIL_PASSWORD,
            hmac_email("reset@example.com"),
            password_hash=hash_password("OldPass1!"),
            email_encrypted=encrypt_email("reset@example.com"),
        )
        await repo.mark_email_verified(method.id)
        raw, token_hash = generate_token()
        await repo.create_reset_token(user.id, token_hash, utc_now() + timedelta(hours=1))
        await session.commit()

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
