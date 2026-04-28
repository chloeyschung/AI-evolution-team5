"""Shared pytest fixtures for all tests."""

import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.ai.metadata_extractor import ContentMetadata
from src.constants import ContentType
from src.ingestion.extractor import ContentExtractor
from src.ai.metadata_extractor import MetadataExtractor
from src.api.app import app
from src.auth.tokens import create_access_token, create_refresh_token
from src.data.models import (
    AccountDeletion,
    AuditLog,
    Base,
    SwipeHistory,
    Content,
    ContentTag,
    UserProfile,
    UserPreferences,
    InterestTag,
    IntegrationTokens,
    IntegrationSyncConfig,
    IntegrationSyncLog,
    AchievementDefinition,
    UserAchievement,
    UserStreak,
    ReminderPreference,
    ReminderLog,
    UserActivityPattern,
    AuthenticationToken,
    UserAuthMethod,
    EmailVerificationToken,
    PasswordResetToken,
)
from src.data import database as db_module


# ============================================================================
# Shared Test Database Setup (for API integration tests only)
# ============================================================================

# Use file-based SQLite for reliable test isolation
# File-based avoids issues with in-memory DB not persisting across connections
import os

# Use a temp-dir SQLite file so tests don't depend on repo mount permissions.
# Some environments mount the repo path as read-only for SQLite write/locking.
import tempfile

TEST_DATABASE_PATH = os.path.join(tempfile.gettempdir(), "briefly_test_briefly.db")
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


async def _clear_all_test_data(session: AsyncSession) -> None:
    """Delete test data in FK-safe child-before-parent order."""
    await session.execute(delete(AuditLog))
    await session.execute(delete(SwipeHistory))
    await session.execute(delete(ContentTag))
    await session.execute(delete(UserActivityPattern))
    await session.execute(delete(ReminderLog))
    await session.execute(delete(ReminderPreference))
    await session.execute(delete(UserAchievement))
    await session.execute(delete(UserStreak))
    await session.execute(delete(AchievementDefinition))
    await session.execute(delete(IntegrationSyncLog))
    await session.execute(delete(IntegrationSyncConfig))
    await session.execute(delete(IntegrationTokens))
    await session.execute(delete(AuthenticationToken))
    await session.execute(delete(PasswordResetToken))
    await session.execute(delete(EmailVerificationToken))
    await session.execute(delete(UserAuthMethod))
    await session.execute(delete(InterestTag))
    await session.execute(delete(UserPreferences))
    await session.execute(delete(Content))
    await session.execute(delete(AccountDeletion))
    await session.execute(delete(UserProfile))
    await session.commit()


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
        await _clear_all_test_data(session)


@pytest.fixture(scope="function", name="db_session")
async def test_db_session():
    """Provide an async database session for tests.

    Use this fixture when you need direct database access via a session.
    Example: async def test_xxx(db_session: AsyncSession): ...
    """
    # Create tables if they don't exist
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Clear all data before test
    async with AsyncTestingSessionLocal() as session:
        await _clear_all_test_data(session)

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


@pytest.fixture
async def test_user(db, db_session: AsyncSession):
    """Create a test user and return the user ID.

    Use this fixture when you need a user in the database for testing.
    Example: async def test_xxx(test_user: int): ...
    """
    from src.utils.datetime_utils import utc_now
    from src.utils.token_hashing import hash_access_token
    from src.constants import AuthProvider
    from datetime import timedelta

    user = UserProfile(
        email="test@example.com",
        display_name=None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    await db_session.flush()

    # Create Google auth method row (replaces google_sub)
    auth_method = UserAuthMethod(
        user_id=user.id,
        provider=AuthProvider.GOOGLE,
        provider_id="test_google_sub_123",
        email_verified=True,
        verified_at=utc_now(),
    )
    db_session.add(auth_method)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()
    expires_at = utc_now() + timedelta(hours=1)

    auth_token = AuthenticationToken(
        user_id=user.id,
        access_token=hash_access_token(access_token),
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    db_session.add(auth_token)
    await db_session.commit()

    return user.id


@pytest.fixture
async def auth_token(test_user: int) -> str:
    """Generate a test JWT access token.

    Use this fixture when you need an authentication token for API calls.
    Example: async def test_xxx(auth_token: str): ...
    """
    return create_access_token(test_user)


@pytest.fixture
async def authenticated_client(db, auth_token: str):
    """Async test client with authentication headers.

    Requires the db fixture and provides an authenticated client.
    Use this for testing endpoints that require authentication.
    Example: async def test_xxx(authenticated_client): ...
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as client:
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


@pytest.fixture(autouse=True)
def setup_share_handler():
    """Initialize ShareHandler for testing (without summarizer)."""
    from src.ingestion.share_handler import ShareHandler

    app.state.share_handler = ShareHandler(
        content_extractor=ContentExtractor(),
        metadata_extractor=None,
        summarizer=None,
    )
    yield
