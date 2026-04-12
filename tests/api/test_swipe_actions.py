"""Tests for UX-002 Swipe Actions API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from src.api.app import app
from src.data.models import Base, SwipeHistory, Content, SwipeAction

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
    db = TestingSessionLocal()
    try:
        db.execute(delete(SwipeHistory))
        db.execute(delete(Content))
        db.commit()
    finally:
        db.close()


client = TestClient(app)


class TestBatchSwipeEndpoints:
    """Tests for batch swipe recording."""

    def test_record_batch_swipes(self):
        """Test recording multiple swipe actions atomically."""
        # Create multiple contents
        content_ids = []
        for i in range(5):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/batch-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Record batch swipe
        response = client.post(
            "/api/v1/swipe",
            json={
                "actions": [
                    {"content_id": content_ids[0], "action": "keep"},
                    {"content_id": content_ids[1], "action": "discard"},
                    {"content_id": content_ids[2], "action": "keep"},
                ]
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["recorded"] == 3
        assert len(data["results"]) == 3

        # Verify all actions were recorded correctly
        actions = {r["content_id"]: r["action"] for r in data["results"]}
        assert actions[content_ids[0]] == "keep"
        assert actions[content_ids[1]] == "discard"
        assert actions[content_ids[2]] == "keep"

    def test_record_single_swipe_still_works(self):
        """Test backward compatibility with single swipe API."""
        # Create content
        response = client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/single-swipe",
            },
        )
        content_id = response.json()["id"]

        # Record single swipe (old format)
        response = client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content_id"] == content_id
        assert data["action"] == "keep"
        assert "id" in data  # Returns created record ID


class TestKeptContentEndpoints:
    """Tests for GET /content/kept endpoint."""

    def test_get_kept_content(self):
        """Test retrieving kept content."""
        # Create and keep some content
        kept_ids = []
        discarded_ids = []
        for i in range(5):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/kept-{i}",
                },
            )
            kept_ids.append(response.json()["id"])

            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/discard-{i}",
                },
            )
            discarded_ids.append(response.json()["id"])

        # Keep the first batch
        for content_id in kept_ids:
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Discard the second batch
        for content_id in discarded_ids:
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "discard"},
            )

        # Get kept content
        response = client.get("/api/v1/content/kept")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify only kept content is returned
        returned_ids = [c["id"] for c in data]
        for content_id in kept_ids:
            assert content_id in returned_ids
        for content_id in discarded_ids:
            assert content_id not in returned_ids

    def test_get_kept_empty(self):
        """Test empty kept list when no content is kept."""
        # Create content but don't keep it
        client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/no-keep",
            },
        )

        # Get kept content
        response = client.get("/api/v1/content/kept")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_kept_pagination(self):
        """Test pagination for kept content."""
        # Create and keep 10 content items
        for i in range(10):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/paginate-{i}",
                },
            )
            content_id = response.json()["id"]
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Get with limit=5
        response = client.get("/api/v1/content/kept?limit=5")
        data = response.json()
        assert len(data) == 5

        # Get with offset=5
        response = client.get("/api/v1/content/kept?limit=5&offset=5")
        data = response.json()
        assert len(data) == 5


class TestDiscardedContentEndpoints:
    """Tests for GET /content/discarded endpoint."""

    def test_get_discarded_content(self):
        """Test retrieving discarded content."""
        # Create and discard some content
        discarded_ids = []
        kept_ids = []
        for i in range(5):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/discard-test-{i}",
                },
            )
            discarded_ids.append(response.json()["id"])

            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/keep-test-{i}",
                },
            )
            kept_ids.append(response.json()["id"])

        # Discard the first batch
        for content_id in discarded_ids:
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "discard"},
            )

        # Keep the second batch
        for content_id in kept_ids:
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_id, "action": "keep"},
            )

        # Get discarded content
        response = client.get("/api/v1/content/discarded")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify only discarded content is returned
        returned_ids = [c["id"] for c in data]
        for content_id in discarded_ids:
            assert content_id in returned_ids
        for content_id in kept_ids:
            assert content_id not in returned_ids

    def test_get_discarded_empty(self):
        """Test empty discarded list when no content is discarded."""
        # Create content but don't discard it
        client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/no-discard",
            },
        )

        # Get discarded content
        response = client.get("/api/v1/content/discarded")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestStatsEndpoint:
    """Tests for GET /stats endpoint."""

    def test_stats_endpoint(self):
        """Test accurate statistics counts."""
        # Create 10 content items
        content_ids = []
        for i in range(10):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/stats-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Keep 4 items
        for i in range(4):
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_ids[i], "action": "keep"},
            )

        # Discard 3 items
        for i in range(4, 7):
            client.post(
                "/api/v1/swipe",
                json={"content_id": content_ids[i], "action": "discard"},
            )

        # Get stats
        response = client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify counts: 10 total, 4 kept, 3 discarded, 3 pending
        assert data["kept"] == 4
        assert data["discarded"] == 3
        assert data["pending"] == 3  # 10 - 4 - 3 = 3

    def test_stats_empty(self):
        """Test stats with no content."""
        response = client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 0
        assert data["kept"] == 0
        assert data["discarded"] == 0


class TestSwipeMutualExclusivity:
    """Tests for edge cases and mutual exclusivity."""

    def test_kept_and_discarded_mutually_exclusive(self):
        """Test that same content cannot be both kept and discarded."""
        # Create content
        response = client.post(
            "/api/v1/content",
            json={
                "platform": "Test",
                "content_type": "article",
                "url": "https://example.com/mutual-exclude",
            },
        )
        content_id = response.json()["id"]

        # Keep the content
        client.post(
            "/api/v1/swipe",
            json={"content_id": content_id, "action": "keep"},
        )

        # Get kept and verify content is there
        kept_response = client.get("/api/v1/content/kept")
        kept_ids = [c["id"] for c in kept_response.json()]
        assert content_id in kept_ids

        # Get discarded and verify content is NOT there
        discarded_response = client.get("/api/v1/content/discarded")
        discarded_ids = [c["id"] for c in discarded_response.json()]
        assert content_id not in discarded_ids

    def test_pending_excludes_kept_and_discarded(self):
        """Test that pending content excludes all swiped items."""
        # Create 3 content items
        content_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/content",
                json={
                    "platform": "Test",
                    "content_type": "article",
                    "url": f"https://example.com/pending-exclude-{i}",
                },
            )
            content_ids.append(response.json()["id"])

        # Keep item 0, discard item 1, leave item 2 pending
        client.post(
            "/api/v1/swipe",
            json={"content_id": content_ids[0], "action": "keep"},
        )
        client.post(
            "/api/v1/swipe",
            json={"content_id": content_ids[1], "action": "discard"},
        )

        # Get pending - should only return item 2
        response = client.get("/api/v1/content/pending")
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == content_ids[2]
