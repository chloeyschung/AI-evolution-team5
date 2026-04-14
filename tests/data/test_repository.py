"""Tests for repository operations."""

import pytest
from datetime import datetime, timezone

from src.ai.metadata_extractor import ContentMetadata, ContentType
from src.data.models import SwipeAction, Content, UserProfile
from src.data.repository import ContentRepository, SwipeRepository
from src.utils.datetime_utils import utc_now


# Import shared test fixtures from conftest
from tests.conftest import test_async_engine, AsyncTestingSessionLocal, Base
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="function")
async def db_session(db):
    """Create database session for testing using shared fixtures.

    The 'db' fixture ensures tables are created and data is cleared.
    """
    async with AsyncTestingSessionLocal() as session:
        yield session


@pytest.fixture
async def test_user_id(db_session: AsyncSession):
    """Create a test user and return the user ID."""
    from sqlalchemy.ext.asyncio import AsyncSession

    user = UserProfile(
        email="test@example.com",
        google_sub="test_google_sub",
        display_name="Test User",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


@pytest.fixture
def sample_metadata():
    """Create sample ContentMetadata."""
    return ContentMetadata(
        platform="YouTube",
        content_type=ContentType.VIDEO,
        url="https://youtube.com/watch?v=test123",
        title="Test Video",
        author="Test Author",
        timestamp=datetime.now(timezone.utc),
    )


class TestContentRepository:
    """Tests for ContentRepository."""

    @pytest.mark.asyncio
    async def test_save_new_content(self, db_session, sample_metadata):
        """Test saving new content."""
        repo = ContentRepository(db_session)
        result = await repo.save(sample_metadata)

        assert result.id is not None
        assert result.platform == "YouTube"
        assert result.content_type == "video"
        assert result.url == "https://youtube.com/watch?v=test123"

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, db_session, sample_metadata):
        """Test saving updates existing content by URL."""
        repo = ContentRepository(db_session)

        # Save initial content
        await repo.save(sample_metadata)

        # Update metadata
        updated_metadata = ContentMetadata(
            platform="YouTube",
            content_type=ContentType.VIDEO,
            url="https://youtube.com/watch?v=test123",
            title="Updated Title",
            author="Updated Author",
            timestamp=datetime.now(timezone.utc),
        )
        result = await repo.save(updated_metadata)

        assert result.title == "Updated Title"
        assert result.author == "Updated Author"

    @pytest.mark.asyncio
    async def test_get_by_url(self, db_session, sample_metadata):
        """Test getting content by URL."""
        repo = ContentRepository(db_session)

        # Save content
        await repo.save(sample_metadata)

        # Get by URL
        result = await repo.get_by_url("https://youtube.com/watch?v=test123")

        assert result is not None
        assert result.url == "https://youtube.com/watch?v=test123"

    @pytest.mark.asyncio
    async def test_get_by_url_not_found(self, db_session):
        """Test getting non-existent content by URL."""
        repo = ContentRepository(db_session)
        result = await repo.get_by_url("https://nonexistent.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, db_session, test_user_id):
        """Test getting all content."""
        repo = ContentRepository(db_session)

        # Save multiple contents
        for i in range(5):
            metadata = ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url=f"https://example.com/{i}",
                title=f"Title {i}",
            )
            await repo.save(metadata)

        results = await repo.get_all(test_user_id, limit=10)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_all_pagination(self, db_session, test_user_id):
        """Test pagination in get_all."""
        repo = ContentRepository(db_session)

        # Save multiple contents
        for i in range(10):
            metadata = ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url=f"https://example.com/{i}",
                title=f"Title {i}",
            )
            await repo.save(metadata)

        results = await repo.get_all(test_user_id, limit=5, offset=0)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_kept(self, db_session, test_user_id):
        """Test getting kept content."""
        content_repo = ContentRepository(db_session)
        swipe_repo = SwipeRepository(db_session)

        # Save contents
        content1 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/1",
            )
        )
        content2 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/2",
            )
        )

        # Record swipe actions
        await swipe_repo.record_swipe(content1.id, SwipeAction.KEEP)
        await swipe_repo.record_swipe(content2.id, SwipeAction.DISCARD)

        kept = await content_repo.get_kept(test_user_id)

        assert len(kept) == 1
        assert kept[0].url == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_get_pending_returns_unswiped_content(self, db_session, test_user_id):
        """Test getting pending content (no swipe history)."""
        content_repo = ContentRepository(db_session)
        swipe_repo = SwipeRepository(db_session)

        # Save contents
        content1 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/1",
            )
        )
        content2 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/2",
            )
        )
        content3 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/3",
            )
        )

        # Swipe only content1
        await swipe_repo.record_swipe(content1.id, SwipeAction.KEEP)

        pending = await content_repo.get_pending(test_user_id)

        assert len(pending) == 2
        pending_urls = [c.url for c in pending]
        assert "https://example.com/2" in pending_urls
        assert "https://example.com/3" in pending_urls
        assert "https://example.com/1" not in pending_urls

    @pytest.mark.asyncio
    async def test_get_pending_excludes_all_swiped_content(self, db_session, test_user_id):
        """Test that pending excludes content with any swipe action."""
        content_repo = ContentRepository(db_session)
        swipe_repo = SwipeRepository(db_session)

        # Save contents
        content1 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/1",
            )
        )
        content2 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/2",
            )
        )
        content3 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/3",
            )
        )

        # Swipe all with different actions
        await swipe_repo.record_swipe(content1.id, SwipeAction.KEEP)
        await swipe_repo.record_swipe(content2.id, SwipeAction.DISCARD)
        await swipe_repo.record_swipe(content3.id, SwipeAction.KEEP)

        pending = await content_repo.get_pending(test_user_id)

        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_get_pending_respects_limit(self, db_session, test_user_id):
        """Test that limit parameter works correctly."""
        content_repo = ContentRepository(db_session)

        # Save multiple contents
        for i in range(10):
            await content_repo.save(
                ContentMetadata(
                    platform="Test",
                    content_type=ContentType.ARTICLE,
                    url=f"https://example.com/{i}",
                )
            )

        pending = await content_repo.get_pending(test_user_id, limit=5)

        assert len(pending) == 5

    @pytest.mark.asyncio
    async def test_get_pending_orders_by_recency(self, db_session, test_user_id):
        """Test that pending content is ordered by recency (newest first)."""
        content_repo = ContentRepository(db_session)

        # Save contents with timestamps
        content1 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/1",
            )
        )

        # Small delay to ensure different timestamps
        await db_session.commit()

        content2 = await content_repo.save(
            ContentMetadata(
                platform="Test",
                content_type=ContentType.ARTICLE,
                url="https://example.com/2",
            )
        )

        pending = await content_repo.get_pending(test_user_id)

        assert len(pending) == 2
        assert pending[0].url == "https://example.com/2"  # Newest first
        assert pending[1].url == "https://example.com/1"


class TestSwipeRepository:
    """Tests for SwipeRepository."""

    @pytest.mark.asyncio
    async def test_record_swipe(self, db_session):
        """Test recording swipe action."""
        repo = SwipeRepository(db_session)

        history = await repo.record_swipe(content_id=1, action=SwipeAction.KEEP)

        assert history.id is not None
        assert history.content_id == 1
        assert history.action == SwipeAction.KEEP

    @pytest.mark.asyncio
    async def test_get_history(self, db_session):
        """Test getting swipe history."""
        repo = SwipeRepository(db_session)

        # Record multiple swipes
        await repo.record_swipe(1, SwipeAction.KEEP)
        await repo.record_swipe(1, SwipeAction.DISCARD)
        await repo.record_swipe(2, SwipeAction.KEEP)

        history = await repo.get_history(1)

        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_history_empty(self, db_session):
        """Test getting empty swipe history."""
        repo = SwipeRepository(db_session)
        history = await repo.get_history(999)

        assert len(history) == 0
