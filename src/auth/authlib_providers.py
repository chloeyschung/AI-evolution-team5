"""Authlib OAuth2 provider configurations (AUTH-005).

Each provider is an AsyncOAuth2Client config. Google is active; others
are scaffolded for future implementation.
"""
from authlib.integrations.httpx_client import AsyncOAuth2Client

from src.config import settings


def get_google_client() -> AsyncOAuth2Client:
    """Return a configured Authlib async client for Google OAuth2."""
    return AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope="openid email profile",
    )


# Scaffolded — implement when adding providers:
# def get_kakao_client() -> AsyncOAuth2Client: ...
# def get_naver_client() -> AsyncOAuth2Client: ...
# def get_github_client() -> AsyncOAuth2Client: ...
