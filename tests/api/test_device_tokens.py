"""Tests for iOS APNs device-token lifecycle endpoints."""

from sqlalchemy import select

from tests.conftest import AsyncTestingSessionLocal
from src.data.models import DeviceToken


async def test_register_device_token_upserts_active_token(authenticated_client, db):
    response = await authenticated_client.post(
        "/api/v1/user/device-token",
        json={"device_token": "apns-token-1", "platform": "ios"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["device_token"] == "apns-token-1"
    assert data["platform"] == "ios"
    assert data["is_active"] is True
    assert data["last_seen_at"].endswith("Z")

    async with AsyncTestingSessionLocal() as session:
        token = (
            await session.execute(select(DeviceToken).where(DeviceToken.device_token == "apns-token-1"))
        ).scalar_one()
        assert token.is_active is True


async def test_delete_device_token_deactivates_token(authenticated_client, db):
    await authenticated_client.post(
        "/api/v1/user/device-token",
        json={"device_token": "apns-token-2", "platform": "ios"},
    )

    response = await authenticated_client.request(
        "DELETE",
        "/api/v1/user/device-token",
        json={"device_token": "apns-token-2", "platform": "ios"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False

    async with AsyncTestingSessionLocal() as session:
        token = (
            await session.execute(select(DeviceToken).where(DeviceToken.device_token == "apns-token-2"))
        ).scalar_one()
        assert token.is_active is False
