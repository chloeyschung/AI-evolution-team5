"""Web OAuth code exchange must use the WEB client credentials, not the native/iOS ones.

Regression guard for the multi-platform Google OAuth split: native (iOS) sign-in
verifies id_token audience against GOOGLE_CLIENT_ID, while the web dashboard performs
server-side authorization-code exchange under a separate confidential client
(GOOGLE_WEB_CLIENT_ID / GOOGLE_WEB_CLIENT_SECRET). Exchanging a web-issued code with
the iOS client_id triggers Google's `invalid_client`.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.config import settings


@pytest.mark.asyncio
async def test_google_code_exchange_uses_web_client_credentials(async_client, db, monkeypatch):
    """POST /auth/google/code forwards GOOGLE_WEB_CLIENT_ID/SECRET (not the iOS client) to the exchange."""
    # Distinct values so a regression to the iOS client_id is unambiguous.
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "ios-client.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "ios-secret-should-not-be-used")
    monkeypatch.setattr(settings, "GOOGLE_WEB_CLIENT_ID", "web-client.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_WEB_CLIENT_SECRET", "web-secret-expected")

    fake_user_info = {
        "sub": "google-sub-web-001",
        "email": "web-oauth@example.com",
        "name": "Web OAuth User",
        "picture": None,
        "email_verified": True,
    }

    with patch(
        "src.auth.google_oauth.exchange_auth_code_for_tokens",
        new_callable=AsyncMock,
        return_value=("fake-id-token", fake_user_info),
    ) as mock_exchange:
        resp = await async_client.post(
            "/api/v1/auth/google/code",
            json={"code": "fake-auth-code"},
        )

    assert resp.status_code == 200, resp.json()
    kwargs = mock_exchange.call_args.kwargs
    assert kwargs["client_id"] == "web-client.apps.googleusercontent.com"
    assert kwargs["client_secret"] == "web-secret-expected"
    # The iOS client must never be used for the web code exchange.
    assert kwargs["client_id"] != "ios-client.apps.googleusercontent.com"
