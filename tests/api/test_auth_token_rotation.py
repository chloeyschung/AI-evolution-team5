"""Behavioral tests for refresh token rotation security (Task 14).

Verifies rotation semantics while allowing a short replay grace for
near-simultaneous mobile refresh requests.
"""

import asyncio

import pytest

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user
from src.data.auth_repository import AuthenticationRepository


async def _login_and_get_refresh_token(async_client, email: str, password: str = "Pass1!") -> str:
    async with AsyncTestingSessionLocal() as session:
        await make_user(session, email=email, password=password)

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.json()
    return login_resp.json()["refresh_token"]


async def test_refresh_token_is_invalidated_after_first_use(async_client, db):
    """Original refresh token is rejected after the mobile retry grace expires.

    Flow:
      1. Login → receive refresh_token_v1
      2. POST /auth/refresh with refresh_token_v1 → get refresh_token_v2
      3. Expire the replay grace
      4. POST /auth/refresh with refresh_token_v1 again → must return 401
    """
    refresh_token_v1 = await _login_and_get_refresh_token(async_client, "rotation@example.com")

    resp1 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert resp1.status_code == 200, f"First refresh failed: {resp1.json()}"
    refresh_token_v2 = resp1.json()["refresh_token"]
    assert refresh_token_v2 != refresh_token_v1, "Token was not rotated on first use"

    AuthenticationRepository._refresh_replay_cache.clear()
    resp2 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert resp2.status_code == 401, (
        f"Expected 401 for consumed refresh token, got {resp2.status_code}: {resp2.json()}"
    )


async def test_concurrent_refresh_replays_rotated_token_during_grace(async_client, db):
    """Near-simultaneous refresh calls with the same token should not log the user out."""
    refresh_token_v1 = await _login_and_get_refresh_token(async_client, "rotation-race@example.com")

    first, second = await asyncio.gather(
        async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_v1}),
        async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_v1}),
    )

    assert first.status_code == 200, first.json()
    assert second.status_code == 200, second.json()
    assert first.json()["refresh_token"] == second.json()["refresh_token"]
    assert first.json()["access_token"] == second.json()["access_token"]


@pytest.fixture(autouse=True)
def clear_refresh_replay_cache():
    AuthenticationRepository._refresh_replay_cache.clear()
    yield
    AuthenticationRepository._refresh_replay_cache.clear()
