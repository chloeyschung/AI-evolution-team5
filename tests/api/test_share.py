"""Tests for Share API endpoints."""

import pytest


class TestShareEndpoint:
    """Tests for POST /share endpoint."""

    async def test_share_url_success(self, authenticated_client):
        """Test sharing a URL successfully."""
        response = await authenticated_client.post(
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

    async def test_share_plain_text(self, authenticated_client):
        """Test sharing plain text content."""
        response = await authenticated_client.post(
            "/api/v1/share",
            json={"content": "This is some plain text I want to save."},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "clipboard"
        assert data["content_type"] == "article"
        assert "This is some plain text" in data.get("title", "")

    async def test_share_empty_content(self, authenticated_client):
        """Test sharing empty content raises validation error."""
        response = await authenticated_client.post(
            "/api/v1/share",
            json={"content": ""},
        )

        assert response.status_code == 422  # Validation error

    async def test_share_duplicate_url(self, authenticated_client):
        """Test sharing the same URL twice updates existing content."""
        # First share
        response1 = await authenticated_client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article"},
        )
        assert response1.status_code == 201
        first_id = response1.json()["id"]

        # Second share with same URL
        response2 = await authenticated_client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article"},
        )
        assert response2.status_code == 201
        second_id = response2.json()["id"]

        # Should return the same ID (updated existing)
        assert first_id == second_id

    async def test_share_with_platform(self, authenticated_client):
        """Test sharing content with platform metadata."""
        response = await authenticated_client.post(
            "/api/v1/share",
            json={"content": "https://example.com/article", "platform": "ios_share"},
        )

        assert response.status_code == 201

    async def test_share_invalid_url(self, authenticated_client):
        """Test sharing an invalid URL is treated as plain text."""
        response = await authenticated_client.post(
            "/api/v1/share",
            json={"content": "not-a-valid-url"},
        )

        # Should treat as plain text, not error
        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "clipboard"
