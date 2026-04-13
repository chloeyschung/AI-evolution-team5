"""Tests for Share API endpoints."""

import pytest
import httpx
from httpx import ASGITransport

from src.api.app import app
from src.ingestion.share_handler import ShareHandler
from src.api.routes import _set_share_handler
from src.ingestion.extractor import ContentExtractor


# Initialize ShareHandler for testing (without summarizer)
test_share_handler = _set_share_handler(
    ShareHandler(
        content_extractor=ContentExtractor(),
        metadata_extractor=None,
        summarizer=None,
    )
)


@pytest.fixture
async def client():
    """Create async test client."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestShareEndpoint:
    """Tests for POST /share endpoint."""

    async def test_share_url_success(self, client):
        """Test sharing a URL successfully."""
        response = await client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["platform"] == "Example"  # Platform is capitalized domain
        assert data["content_type"] == "article"
        assert data["url"] == "https://example.com/article"
        assert "created_at" in data

    async def test_share_plain_text(self, client):
        """Test sharing plain text content."""
        response = await client.post(
            "/api/v1/share",
            json={"content": "This is some plain text I want to save."},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "clipboard"
        assert data["content_type"] == "article"
        assert "This is some plain text" in data.get("title", "")

    async def test_share_empty_content(self, client):
        """Test sharing empty content raises validation error."""
        response = await client.post(
            "/api/v1/share",
            json={"content": ""},
        )

        assert response.status_code == 422  # Validation error

    async def test_share_duplicate_url(self, client):
        """Test sharing the same URL twice updates existing content."""
        # First share
        response1 = await client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article"},
        )
        assert response1.status_code == 201
        first_id = response1.json()["id"]

        # Second share with same URL
        response2 = await client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article"},
        )
        assert response2.status_code == 201
        second_id = response2.json()["id"]

        # Should return the same ID (updated existing)
        assert first_id == second_id

    async def test_share_with_platform(self, client):
        """Test sharing content with platform metadata."""
        response = await client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article", "platform": "ios_share"},
        )

        assert response.status_code == 201

    async def test_share_invalid_url(self, client):
        """Test sharing an invalid URL is treated as plain text."""
        response = await client.post(
            "/api/v1/share",
            json={"content": "not-a-valid-url"},
        )

        # Should treat as plain text, not error
        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "clipboard"
