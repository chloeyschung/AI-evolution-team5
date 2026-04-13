"""Shared pytest fixtures for all tests."""

import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.ai.metadata_extractor import ContentMetadata, ContentType
from src.ingestion.extractor import ContentExtractor
from src.ai.metadata_extractor import MetadataExtractor
from src.api.app import app
from src.data.models import Base, SwipeHistory, Content
from src.data import database as db_module


# ============================================================================
# Shared Test Database Setup
# ============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_briefly_async.db"
test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncTestingSessionLocal = async_sessionmaker(
    test_async_engine, autocommit=False, autoflush=False
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


@pytest.fixture(scope="module", autouse=True)
async def create_test_tables():
    """Create test tables before running tests."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function", autouse=True)
async def clear_test_data():
    """Clear test data before each test."""
    async with AsyncTestingSessionLocal() as db:
        await db.execute(delete(SwipeHistory))
        await db.execute(delete(Content))
        await db.commit()


@pytest.fixture
async def async_client():
    """Async test client fixture."""
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
