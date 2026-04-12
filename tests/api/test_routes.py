"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.api.app import app
from src.data.models import Base, SwipeHistory, Content, SwipeAction
from src.ai.metadata_extractor import ContentMetadata, ContentType

# Create test database using SQLite (sync for TestClient)
TEST_DATABASE_URL = "sqlite:///./test_briefly.db"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# Override the app's database dependency
from src.data import database as db_module


def sync_get_db():
    """Sync database dependency for testing with TestClient."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[db_module.get_db] = sync_get_db


@pytest.fixture(scope="module", autouse=True)
def create_test_tables():
    """Create test tables before running tests."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def clear_test_data():
    """Clear test data before each test."""
    from sqlalchemy import delete

    db = TestingSessionLocal()
    try:
        db.execute(delete(SwipeHistory))
        db.execute(delete(Content))
        db.commit()
    finally:
        db.close()


client = TestClient(app)


class TestContentEndpoints:
    """Tests for content API endpoints."""

    def test_create_content(self):
        """Test creating new content."""
        response = client.post(
            "/api/v1/content",
            json={
                "platform": "YouTube",
                "content_type": "video",
                "url": "https://youtube.com/watch?v=test123",
                "title": "Test Video",
                "author": "Test Author",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "YouTube"
        assert data["content_type"] == "video"
        assert data["url"] == "https://youtube.com/watch?v=test123"
        assert data["id"] is not None

    def test_create_content_minimal(self):
        """Test creating content with minimal fields."""
        response = client.post(
            "/api/v1/content",
            json={
                "platform": "Web",
                "content_type": "article",
                "url": "https://example.com/article",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "Web"
        assert data["title"] is None
        assert data["author"] is None

    def test_list_content(self):
        """Test listing all content."""
        response = client.get("/api/v1/content")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_content_with_limit(self):
        """Test listing content with limit parameter."""
        response = client.get("/api/v1/content?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10


class TestSwipeEndpoints:
    """Tests for swipe API endpoints."""

    def test_record_swipe_keep(self):
        """Test recording KEEP swipe action."""
        # First create a content
        create_response = client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content_id"] == content_id
        assert data["action"] == "keep"

    def test_record_swipe_discard(self):
        """Test recording DISCARD swipe action."""
        # First create a content
        create_response = client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swipe-test-2",
            },
        )
        content_id = create_response.json()["id"]

        # Record swipe
        response = client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "discard"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "discard"


class TestPendingContentEndpoints:
    """Tests for pending content API endpoints."""

    def test_get_pending_content(self):
        """Test getting pending content (no swipe history)."""
        # Create contents
        client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-1",
            },
        )
        client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/pending-2",
            },
        )

        # Get pending content
        response = client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_pending_empty(self):
        """Test getting pending content when all content is swiped."""
        # Create and swipe content
        create_response = client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/swiped",
            },
        )
        content_id = create_response.json()["id"]

        # Swipe the content
        client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get pending content
        response = client.get("/api/v1/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_pending_limit(self):
        """Test pending content with limit parameter."""
        # Create multiple contents
        for i in range(10):
            client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/limit-test-{i}",
                },
            )

        # Get pending content with limit
        response = client.get("/api/v1/content/pending?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_root_endpoint(self):
        """Test root endpoint returns health check."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "briefly-api"
