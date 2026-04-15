"""Configuration settings for Briefly."""

import os
from functools import lru_cache


@lru_cache
def get_settings():
    """Get application settings from environment variables.

    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


class Settings:
    """Application settings."""

    # JWT Settings
    _jwt_secret_key: str | None = os.getenv("JWT_SECRET_KEY")
    if _jwt_secret_key is None:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    if len(_jwt_secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters for security")
    JWT_SECRET_KEY: str = _jwt_secret_key
    JWT_ALGORITHM: str = "HS256"

    # TODO #1 (2026-04-14): ENCRYPTION_KEY validation moved from token_encryption.py
    # Encryption Key Settings - validated at startup for fail-fast behavior
    _encryption_key: str | None = os.getenv("ENCRYPTION_KEY")
    if _encryption_key is None:
        raise RuntimeError("ENCRYPTION_KEY environment variable is required for OAuth token encryption")
    ENCRYPTION_KEY: str = _encryption_key

    # Google OAuth Settings - validated at startup for fail-fast behavior
    _google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    if _google_client_id is None:
        raise RuntimeError("GOOGLE_CLIENT_ID environment variable is required for Google OAuth audience validation")
    GOOGLE_CLIENT_ID: str = _google_client_id

    _google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    if _google_client_secret is None:
        raise RuntimeError(
            "GOOGLE_CLIENT_SECRET environment variable is required for OAuth code exchange"
        )
    GOOGLE_CLIENT_SECRET: str = _google_client_secret

    _google_redirect_uri: str | None = os.getenv("GOOGLE_REDIRECT_URI")
    if _google_redirect_uri is None:
        raise RuntimeError(
            "GOOGLE_REDIRECT_URI environment variable is required for OAuth code exchange"
        )
    GOOGLE_REDIRECT_URI: str = _google_redirect_uri

    # API Settings
    API_PREFIX: str = "/api/v1"

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./briefly.db")

    # VLLM Settings (for AI summarization)
    VLLM_SERVER_URL: str = os.getenv("VLLM_SERVER_URL", "http://localhost:8000")
    VLLM_MODEL: str = os.getenv("VLLM_MODEL", "default-model")

    # Content Settings
    MAX_SUMMARY_LENGTH: int = 300  # Maximum characters for AI summary


# Convenience access
settings = get_settings()
