"""Tests for Sign in with Apple auth endpoint."""

from tests.conftest import AsyncTestingSessionLocal
from src.constants import AuthProvider
from src.data.email_auth_repository import EmailAuthRepository


async def test_apple_login_creates_user_and_auth_method(async_client, db, monkeypatch):
    async def fake_verify(identity_token: str, bundle_id: str) -> dict[str, str]:
        assert identity_token == "apple.identity.jwt"
        assert bundle_id == "com.briefly.app"
        return {
            "sub": "apple-user-123",
            "email": "apple@example.com",
        }

    monkeypatch.setattr("src.auth.apple_oauth.verify_apple_identity_token", fake_verify)

    response = await async_client.post(
        "/api/v1/auth/apple",
        json={
            "identity_token": "apple.identity.jwt",
            "full_name": "Apple User",
            "email": "apple@example.com",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_at"].endswith("Z")
    assert data["user"]["email"] == "apple@example.com"
    assert data["user"]["display_name"] == "Apple User"
    assert data["is_new_user"] is True

    async with AsyncTestingSessionLocal() as session:
        repo = EmailAuthRepository(session)
        method = await repo.get_auth_method_by_provider(AuthProvider.APPLE, "apple-user-123")
        assert method is not None
        assert method.email_verified is True
