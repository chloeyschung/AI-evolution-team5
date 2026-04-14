"""Tests for LinkedIn integration (INT-002)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.linkedin.client import (
    LinkedInClient,
    LinkedInAuthError,
    LinkedInRateLimitError,
    LinkedInAPIError,
)
from src.integrations.linkedin.models import LinkedInPost, LinkedInSavedItem, LinkedInSyncResult
from src.integrations.linkedin.utils import (
    parse_linkedin_date,
    extract_post_id_from_url,
    normalize_linkedin_urn,
    is_linkedin_url,
)
from src.integrations.repositories.integration import IntegrationRepository
from src.data.models import IntegrationTokens, IntegrationSyncConfig, IntegrationSyncLog


# LinkedIn Client Tests

@pytest.mark.asyncio
async def test_linkedin_client_initialization():
    """Test LinkedIn client initialization with tokens."""
    client = LinkedInClient(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    assert client.access_token == "test_access_token"
    assert client.refresh_token == "test_refresh_token"


@pytest.mark.asyncio
async def test_linkedin_client_minimal():
    """Test LinkedIn client with only access token."""
    client = LinkedInClient(access_token="test_access_token")
    assert client.access_token == "test_access_token"
    assert client.refresh_token is None


# LinkedIn Saved Items API Tests

@pytest.mark.asyncio
async def test_linkedin_client_get_saved_items_success():
    """Test getting saved items from LinkedIn API."""
    client = LinkedInClient(access_token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "elements": [
            {
                "urn": "urn:li:savedItem:123",
                "savedAt": datetime.now(timezone.utc).isoformat(),
                "target": {"urn": "urn:li:share:456"},
            }
        ]
    }

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        items = await client.get_saved_items(count=10)

        assert len(items) == 1
        assert items[0].urn == "urn:li:savedItem:123"
        assert items[0].target_urn == "urn:li:share:456"


@pytest.mark.asyncio
async def test_linkedin_client_get_saved_items_auth_error():
    """Test saved items fails with auth error."""
    client = LinkedInClient(access_token="invalid_token")

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LinkedInAuthError, match="Invalid or expired access token"):
            await client.get_saved_items()


@pytest.mark.asyncio
async def test_linkedin_client_get_saved_items_rate_limit():
    """Test saved items fails with rate limit error."""
    client = LinkedInClient(access_token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 429

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LinkedInRateLimitError, match="Rate limit exceeded"):
            await client.get_saved_items()


@pytest.mark.asyncio
async def test_linkedin_client_get_saved_items_api_error():
    """Test saved items fails with API error."""
    client = LinkedInClient(access_token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LinkedInAPIError):
            await client.get_saved_items()


# LinkedIn Post from URL Tests

@pytest.mark.asyncio
async def test_linkedin_client_get_post_from_url_success():
    """Test extracting post data from LinkedIn URL."""
    client = LinkedInClient(access_token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <head>
    <meta property="og:title" content="Test Post Title" />
    <meta property="og:description" content="Test description" />
    <meta property="og:image" content="https://example.com/image.jpg" />
    </head>
    </html>
    """

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        post = await client.get_post_from_url("https://www.linkedin.com/feed/update/urn:li:share:123/")

        assert post is not None
        assert post.title == "Test Post Title"
        assert post.image_url == "https://example.com/image.jpg"


@pytest.mark.asyncio
async def test_linkedin_client_get_post_from_url_not_found():
    """Test extracting post data from invalid URL."""
    client = LinkedInClient(access_token="test_token")

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("src.integrations.linkedin.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        post = await client.get_post_from_url("https://www.linkedin.com/feed/update/urn:li:share:999/")

        assert post is None


# LinkedIn URN/URL Conversion Tests

def test_linkedin_client_generate_post_url_from_share_urn():
    """Test generating URL from share URN."""
    client = LinkedInClient(access_token="test_token")
    urn = "urn:li:share:1234567890"
    url = client.generate_post_url(urn)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:1234567890/"


def test_linkedin_client_generate_post_url_from_activity_urn():
    """Test generating URL from activity URN."""
    client = LinkedInClient(access_token="test_token")
    urn = "urn:li:activity:1234567890"
    url = client.generate_post_url(urn)
    assert url == "https://www.linkedin.com/feed/update/urn:li:activity:1234567890/"


def test_linkedin_client_generate_post_url_already_url():
    """Test generating URL when input is already a URL."""
    client = LinkedInClient(access_token="test_token")
    url = "https://www.linkedin.com/posts/test"
    result = client.generate_post_url(url)
    assert result == url


def test_linkedin_client_extract_urn_from_url():
    """Test extracting URN from LinkedIn URL."""
    client = LinkedInClient(access_token="test_token")
    url = "https://www.linkedin.com/feed/update/urn:li:share:1234567890/"
    urn = client._extract_urn_from_url(url)
    assert urn == "urn:li:share:1234567890"


def test_linkedin_client_extract_urn_from_url_no_urn():
    """Test extracting URN from URL without URN."""
    client = LinkedInClient(access_token="test_token")
    url = "https://www.linkedin.com/posts/test/123"
    urn = client._extract_urn_from_url(url)
    assert urn is None


# LinkedIn Model Tests

def test_linkedin_saved_item_model():
    """Test LinkedInSavedItem model serialization."""
    saved_at = datetime.now(timezone.utc)
    item = LinkedInSavedItem(
        urn="urn:li:savedItem:123",
        saved_at=saved_at,
        target_urn="urn:li:share:456",
    )
    assert item.urn == "urn:li:savedItem:123"
    assert item.target_urn == "urn:li:share:456"


def test_linkedin_post_model():
    """Test LinkedInPost model serialization."""
    post = LinkedInPost(
        urn="urn:li:share:123",
        url="https://www.linkedin.com/feed/update/urn:li:share:123/",
        title="Test Post",
        author="John Doe",
        author_urn="urn:li:member:456",
        published_at=datetime.now(timezone.utc),
        content_type="text",
        text_content="This is the post content",
        image_url="https://example.com/image.jpg",
    )
    assert post.urn == "urn:li:share:123"
    assert post.title == "Test Post"
    assert post.author == "John Doe"


def test_linkedin_post_model_minimal():
    """Test LinkedInPost model with optional fields."""
    post = LinkedInPost(
        urn="urn:li:share:123",
        url="https://www.linkedin.com/feed/update/urn:li:share:123/",
        title="Test Post",
        author="John Doe",
        author_urn="urn:li:member:456",
    )
    assert post.published_at is None
    assert post.content_type == "text"
    assert post.text_content is None
    assert post.image_url is None


def test_linkedin_sync_result_model():
    """Test LinkedInSyncResult model."""
    result = LinkedInSyncResult(
        ingested=5,
        skipped=2,
        errors=[{"urn": "urn:li:share:123", "error": "test error"}],
    )
    assert result.ingested == 5
    assert result.skipped == 2
    assert len(result.errors) == 1


def test_linkedin_sync_result_empty():
    """Test LinkedInSyncResult with defaults."""
    result = LinkedInSyncResult()
    assert result.ingested == 0
    assert result.skipped == 0
    assert result.errors == []


# LinkedIn Utility Function Tests

def test_parse_linkedin_date_milliseconds():
    """Test parsing LinkedIn date in milliseconds."""
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    result = parse_linkedin_date(str(timestamp))
    assert result is not None
    assert result.tzinfo == timezone.utc


def test_parse_linkedin_date_iso():
    """Test parsing LinkedIn date in ISO format."""
    dt = datetime.now(timezone.utc)
    result = parse_linkedin_date(dt.isoformat())
    assert result is not None
    assert result.tzinfo == timezone.utc


def test_parse_linkedin_date_iso_with_z():
    """Test parsing LinkedIn date in ISO format with Z suffix."""
    result = parse_linkedin_date("2024-01-15T10:30:00Z")
    assert result is not None
    assert result.tzinfo == timezone.utc


def test_parse_linkedin_date_invalid():
    """Test parsing invalid LinkedIn date."""
    result = parse_linkedin_date("invalid")
    assert result is None


def test_parse_linkedin_date_empty():
    """Test parsing empty LinkedIn date."""
    result = parse_linkedin_date("")
    assert result is None


def test_extract_post_id_from_url_feed_update():
    """Test extracting post ID from feed/update URL."""
    url = "https://www.linkedin.com/feed/update/urn:li:share:1234567890/"
    post_id = extract_post_id_from_url(url)
    assert post_id == "1234567890"


def test_extract_post_id_from_url_posts():
    """Test extracting post ID from /posts/ URL."""
    url = "https://www.linkedin.com/posts/johndoe_1234567890/"
    post_id = extract_post_id_from_url(url)
    # Returns the full slug (author_id + post_id)
    assert post_id == "johndoe_1234567890"


def test_extract_post_id_from_url_pulse():
    """Test extracting post ID from /pulse/ URL."""
    url = "https://www.linkedin.com/pulse/article-title-author_1234567890/"
    post_id = extract_post_id_from_url(url)
    # Returns the full slug (title + author + post_id)
    assert post_id == "article-title-author_1234567890"


def test_extract_post_id_from_url_invalid():
    """Test extracting post ID from invalid URL."""
    url = "https://www.google.com"
    post_id = extract_post_id_from_url(url)
    assert post_id is None


def test_normalize_linkedin_urn_standard():
    """Test normalizing standard LinkedIn URN."""
    result = normalize_linkedin_urn("urn:li:share:123")
    assert result == "urn:li:share:123"


def test_normalize_linkedin_urn_with_whitespace():
    """Test normalizing URN with whitespace."""
    result = normalize_linkedin_urn("  urn:li:share:123  ")
    assert result == "urn:li:share:123"


def test_normalize_linkedin_urn_share_prefix():
    """Test normalizing URN with share: prefix."""
    result = normalize_linkedin_urn("share:123")
    assert result == "urn:li:share:123"


def test_normalize_linkedin_urn_raw_id():
    """Test normalizing raw ID to URN."""
    result = normalize_linkedin_urn("123456789")
    assert result == "urn:li:share:123456789"


def test_normalize_linkedin_urn_empty():
    """Test normalizing empty URN."""
    result = normalize_linkedin_urn("")
    assert result == ""


def test_is_linkedin_url_standard():
    """Test detecting standard LinkedIn URL."""
    assert is_linkedin_url("https://www.linkedin.com/feed/update/urn:li:share:123/")
    assert is_linkedin_url("https://linkedin.com/posts/test")


def test_is_linkedin_url_short():
    """Test detecting LinkedIn short URL."""
    assert is_linkedin_url("https://lnkd.in/abc123")


def test_is_linkedin_url_not_linkedin():
    """Test detecting non-LinkedIn URL."""
    assert not is_linkedin_url("https://www.google.com")
    assert not is_linkedin_url("https://www.youtube.com/watch?v=123")


# Integration Repository Tests for LinkedIn

@pytest.mark.asyncio
async def test_integration_repo_linkedin_tokens(db_session):
    """Test saving and getting LinkedIn OAuth tokens."""
    repo = IntegrationRepository(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Save tokens
    token = await repo.save_tokens(
        user_id=1,
        provider="linkedin",
        access_token="test_linkedin_access_token",
        refresh_token="test_linkedin_refresh_token",
        expires_at=expires_at,
    )

    assert token.user_id == 1
    assert token.provider == "linkedin"
    # Tokens are now encrypted at rest, use getter methods
    assert token.get_access_token() == "test_linkedin_access_token"

    # Get tokens
    retrieved = await repo.get_tokens(1, "linkedin")
    assert retrieved is not None
    assert retrieved.get_access_token() == "test_linkedin_access_token"


@pytest.mark.asyncio
async def test_integration_repo_linkedin_sync_config(db_session):
    """Test LinkedIn sync configuration."""
    repo = IntegrationRepository(db_session)

    # Save config
    config = await repo.save_sync_config(
        user_id=1,
        provider="linkedin",
        playlist_id="saved_posts",
        playlist_name="Saved Posts",
        sync_frequency="daily",
        is_active=True,
    )

    assert config.user_id == 1
    assert config.provider == "linkedin"
    assert config.resource_id == "saved_posts"
    assert config.sync_frequency == "daily"
    assert config.is_active == 1


@pytest.mark.asyncio
async def test_integration_repo_linkedin_sync_log(db_session):
    """Test LinkedIn sync log."""
    repo = IntegrationRepository(db_session)

    log = await repo.log_sync(
        user_id=1,
        provider="linkedin",
        resource_id="saved_posts",
        status="success",
        ingested_count=10,
        skipped_count=5,
        error_message=None,
    )

    assert log.user_id == 1
    assert log.provider == "linkedin"
    assert log.status == "success"
    assert log.ingested_count == 10
    assert log.skipped_count == 5


@pytest.mark.asyncio
async def test_integration_repo_linkedin_delete_tokens(db_session):
    """Test deleting LinkedIn OAuth tokens."""
    repo = IntegrationRepository(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Save tokens
    await repo.save_tokens(
        user_id=1,
        provider="linkedin",
        access_token="test_token",
        refresh_token="test_refresh",
        expires_at=expires_at,
    )

    # Delete tokens
    deleted = await repo.delete_tokens(1, "linkedin")
    assert deleted is True

    # Verify deleted
    token = await repo.get_tokens(1, "linkedin")
    assert token is None


@pytest.mark.asyncio
async def test_integration_repo_linkedin_delete_sync_config(db_session):
    """Test deleting LinkedIn sync configuration."""
    repo = IntegrationRepository(db_session)

    # Save config
    await repo.save_sync_config(
        user_id=1,
        provider="linkedin",
        playlist_id="saved_posts",
        playlist_name="Saved Posts",
        sync_frequency="daily",
        is_active=True,
    )

    # Delete config
    deleted = await repo.delete_sync_config(1, "linkedin", "saved_posts")
    assert deleted is True

    # Verify deleted
    configs = await repo.get_sync_configs(1, "linkedin")
    assert len(configs) == 0
