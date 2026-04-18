"""Integration tests for SEC-003: Audit Logging & Security Event Tracking."""

from unittest.mock import patch

from sqlalchemy import select

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user
from src.data.models import AuditLog


async def test_login_success_writes_audit_row(async_client, db):
    """Successful email/password login → LOGIN_SUCCESS row in audit_logs."""
    async with AsyncTestingSessionLocal() as session:
        _, _ = await make_user(session, email="audit_login@example.com", password="Pass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "audit_login@example.com",
        "password": "Pass1!",
    })
    assert resp.status_code == 200

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "login_success")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].user_id is not None


async def test_login_failure_user_not_found_writes_audit_row(async_client, db):
    """Login with unknown email → LOGIN_FAILURE row with reason=user_not_found."""
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "ghost@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "login_failure")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].user_id is None
    assert rows[0].meta is not None
    assert rows[0].meta.get("reason") == "user_not_found"


async def test_login_failure_wrong_password_writes_audit_row(async_client, db):
    """Login with wrong password → LOGIN_FAILURE row with reason=invalid_password."""
    async with AsyncTestingSessionLocal() as session:
        _, _ = await make_user(session, email="wrongpass@example.com", password="CorrectPass!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "WrongPass!",
    })
    assert resp.status_code == 401

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "login_failure")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].meta is not None
    assert rows[0].meta.get("reason") == "invalid_password"


async def test_token_refresh_writes_audit_row(async_client, db):
    """Successful token refresh → REFRESH_TOKEN row in audit_logs."""
    async with AsyncTestingSessionLocal() as session:
        _, access_token = await make_user(session, email="refresh@example.com", password="Pass1!")

    # Get refresh token from login
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "refresh@example.com",
        "password": "Pass1!",
    })
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # Clear audit rows from login before testing refresh
    async with AsyncTestingSessionLocal() as session:
        from sqlalchemy import delete
        await session.execute(delete(AuditLog))
        await session.commit()

    resp = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "refresh_token")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].user_id is not None


async def test_account_delete_initiate_writes_audit_row(async_client, db):
    """Account delete step 1 → ACCOUNT_DELETE_INITIATED row."""
    async with AsyncTestingSessionLocal() as session:
        _, access_token = await make_user(session, email="del_init@example.com", password="Pass1!")

    resp = await async_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "confirmation_token" in resp.json()

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "account_delete_initiated")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].meta is not None
    assert rows[0].meta.get("step") == 1


async def test_account_delete_confirm_writes_audit_row(async_client, db):
    """Account delete step 2 → ACCOUNT_DELETE_CONFIRMED row."""
    async with AsyncTestingSessionLocal() as session:
        _, access_token = await make_user(session, email="del_confirm@example.com", password="Pass1!")

    # Step 1: initiate
    step1 = await async_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert step1.status_code == 200
    confirmation_token = step1.json()["confirmation_token"]

    # Step 2: confirm
    step2 = await async_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True, "confirmation_token": confirmation_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert step2.status_code == 200

    async with AsyncTestingSessionLocal() as session:
        initiated = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "account_delete_initiated")
        )).scalars().all()
        confirmed = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "account_delete_confirmed")
        )).scalars().all()

    assert len(initiated) == 1
    assert len(confirmed) == 1
    assert confirmed[0].meta is not None
    assert confirmed[0].meta.get("step") == 2


async def test_audit_log_user_id_null_for_unknown_user(async_client, db):
    """Pre-auth failure (unknown email) → user_id is NULL in audit log."""
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "doesntmatter",
    })
    assert resp.status_code == 401

    async with AsyncTestingSessionLocal() as session:
        rows = (await session.execute(
            select(AuditLog).where(AuditLog.event_type == "login_failure")
        )).scalars().all()

    assert len(rows) == 1
    assert rows[0].user_id is None
