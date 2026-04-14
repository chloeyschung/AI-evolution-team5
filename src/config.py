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
    JWT_SECRET_KEY: str = _jwt_secret_key
    JWT_ALGORITHM: str = "HS256"

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
