"""Behavioral test for refresh token rotation security (Task 14).

Verifies that a refresh token is invalidated after first use — the semantic
guarantee enforced at the DB level by SELECT FOR UPDATE in the production path.
"""

from sqlalchemy import select

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user
from src.data.models import AuthenticationToken


async def test_refresh_token_is_invalidated_after_first_use(async_client, db):
    """Original refresh token must be rejected after it has been rotated.

    Flow:
      1. Login → receive refresh_token_v1
      2. POST /auth/refresh with refresh_token_v1 → get refresh_token_v2
      3. POST /auth/refresh with refresh_token_v1 again → must return 401

    This confirms the token-rotation security property.  The SELECT FOR UPDATE
    added to get_token_by_refresh_token is the implementation mechanism that
    prevents a concurrent second request from racing past step 3.
    """
    # Step 1: create a verified user and obtain their initial tokens
    async with AsyncTestingSessionLocal() as session:
        user, _access_token = await make_user(session, email="rotation@example.com")
        row = (
            await session.execute(
                select(AuthenticationToken).where(AuthenticationToken.user_id == user.id)
            )
        ).scalar_one()
        refresh_token_v1 = row.refresh_token

    # Step 2: use the refresh token once → rotation produces refresh_token_v2
    resp1 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert resp1.status_code == 200, f"First refresh failed: {resp1.json()}"
    refresh_token_v2 = resp1.json()["refresh_token"]
    assert refresh_token_v2 != refresh_token_v1, "Token was not rotated on first use"

    # Step 3: reuse the original (now-consumed) refresh token → must be 401
    resp2 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert resp2.status_code == 401, (
        f"Expected 401 for consumed refresh token, got {resp2.status_code}: {resp2.json()}"
    )
