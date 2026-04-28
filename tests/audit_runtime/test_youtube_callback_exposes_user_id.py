import os
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_youtube_callback_success_returns_user_id(async_client, db_session):
    """
    Runtime probe: exercise the success path of GET /integrations/youtube/callback and
    assert response body contains user_id (potential exposure surface depending on caller).
    """
    from src.integrations.repositories.integration import IntegrationRepository
    from src.utils.datetime_utils import utc_now

    repo = IntegrationRepository(db_session)
    await repo.save_oauth_state(
        user_id=123,
        provider="youtube",
        state_token="state_ok",
        expires_at=utc_now() + timedelta(minutes=15),
    )
    await db_session.commit()

    os.environ["YOUTUBE_CLIENT_ID"] = "cid"
    os.environ["YOUTUBE_CLIENT_SECRET"] = "csec"

    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
            }

    # integrations.py uses "async with httpx.AsyncClient() as client: await client.post(...)"
    fake_client_cm = AsyncMock()
    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=_FakeResp())
    fake_client_cm.__aenter__.return_value = fake_client
    fake_client_cm.__aexit__.return_value = False

    with patch("src.api.routers.integrations.httpx.AsyncClient", return_value=fake_client_cm):
        resp = await async_client.get(
            "/api/v1/integrations/youtube/callback",
            params={"code": "fake_code", "state": "state_ok"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["message"] == "Connected to YouTube successfully"
    assert body["user_id"] == 123

    os.environ.pop("YOUTUBE_CLIENT_ID", None)
    os.environ.pop("YOUTUBE_CLIENT_SECRET", None)

