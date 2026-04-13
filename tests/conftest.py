"""Shared pytest fixtures for all tests."""

import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.ai.metadata_extractor import ContentMetadata, ContentType
from src.ingestion.extractor import ContentExtractor
from src.ai.metadata_extractor import MetadataExtractor
from src.api.app import app
from src.data.models import (
    Base,
    SwipeHistory,
    Content,
    UserProfile,
    UserPreferences,
    InterestTag,
    IntegrationTokens,
    IntegrationSyncConfig,
    IntegrationSyncLog,
)
from src.data import database as db_module


# ============================================================================
# Shared Test Database Setup (for API integration tests only)
# ============================================================================

# Use file-based SQLite for reliable test isolation
# File-based avoids issues with in-memory DB not persisting across connections
import os

# Use a fixed test database file in the project root
TEST_DATABASE_PATH = "test_briefly.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DATABASE_PATH}"

test_async_engine = create_async_engine(
    TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)
AsyncTestingSessionLocal = async_sessionmaker(
    test_async_engine, class_=AsyncSession, expire_on_commit=False
)


async def async_get_db():
    """Async database dependency for testing."""
    async with AsyncTestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


# Override the app's database dependency with async session
app.dependency_overrides[db_module.get_db] = async_get_db


@pytest.fixture(scope="function", name="db")
async def setup_test_database():
    """Create tables and clear data before each test.

    This fixture must be explicitly requested by tests that need database access.
    Use it as a parameter: async def test_xxx(db): ...
    """
    # Create tables
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup: drop all data after test (keep tables for next test)
    async with AsyncTestingSessionLocal() as session:
        await session.execute(delete(IntegrationSyncLog))
        await session.execute(delete(IntegrationSyncConfig))
        await session.execute(delete(IntegrationTokens))
        await session.execute(delete(InterestTag))
        await session.execute(delete(UserPreferences))
        await session.execute(delete(UserProfile))
        await session.execute(delete(SwipeHistory))
        await session.execute(delete(Content))
        await session.commit()


@pytest.fixture(scope="function", name="db_session")
async def test_db_session():
    """Provide an async database session for tests.

    Use this fixture when you need direct database access via a session.
    Example: async def test_xxx(db_session: AsyncSession): ...
    """
    # Create tables if they don't exist
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncTestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_after_session():
    """Clean up test database file after all tests complete."""
    yield
    if os.path.exists(TEST_DATABASE_PATH):
        try:
            os.remove(TEST_DATABASE_PATH)
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
async def async_client(db):
    """Async test client fixture.

    Requires the db fixture to ensure tables are created before tests run.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def content_extractor_mock():
    """Create mocked ContentExtractor."""
    mock = AsyncMock(spec=ContentExtractor)
    mock.extract_text = AsyncMock(return_value="Extracted content")
    return mock


@pytest.fixture
def metadata_extractor_mock():
    """Create mocked MetadataExtractor."""
    mock = AsyncMock(spec=MetadataExtractor)
    mock.extract_metadata = AsyncMock(
        return_value=ContentMetadata(
            platform="Test",
            content_type=ContentType.ARTICLE,
            url="https://example.com",
        )
    )
    return mock


@pytest.fixture
def metadata_extractor_mock_testplatform():
    """Create mocked MetadataExtractor with TestPlatform."""
    mock = AsyncMock(spec=MetadataExtractor)
    mock.extract_metadata = AsyncMock(
        return_value=ContentMetadata(
            platform="TestPlatform",
            content_type=ContentType.ARTICLE,
            url="https://example.com",
        )
    )
    return mock
