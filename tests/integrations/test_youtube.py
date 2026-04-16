"""Tests for YouTube integration (INT-001)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.youtube.client import YouTubeClient, YouTubeAuthError, YouTubeAPIError
from src.integrations.youtube.models import YouTubeVideo, YouTubePlaylist, SyncResult
from src.integrations.repositories.integration import IntegrationRepository
from src.data.models import IntegrationTokens, IntegrationSyncConfig, IntegrationSyncLog


# YouTube Client Tests

@pytest.mark.asyncio
async def test_youtube_client_initialization():
    """Test YouTube client initialization with API key."""
    client = YouTubeClient(api_key="test_api_key")
    assert client.api_key == "test_api_key"
    assert client.user_id is None


@pytest.mark.asyncio
async def test_youtube_client_no_api_key():
    """Test YouTube client fails without API key."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(YouTubeAuthError, match="YouTube API key not configured"):
            YouTubeClient()


@pytest.mark.asyncio
async def test_youtube_client_get_access_token_valid():
    """Test getting access token when still valid."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    client = YouTubeClient(
        api_key="test_key",
        access_token="valid_token",
        token_expires_at=expires_at,
    )
    token = await client.get_access_token()
    assert token == "valid_token"


@pytest.mark.asyncio
async def test_youtube_client_get_access_token_expired_no_refresh():
    """Test getting access token fails when expired and no refresh token."""
    expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    client = YouTubeClient(
        api_key="test_key",
        access_token="expired_token",
        token_expires_at=expires_at,
    )
    with pytest.raises(YouTubeAuthError, match="No refresh token available"):
        await client.get_access_token()


@pytest.mark.asyncio
async def test_youtube_client_refresh_token():
    """Test token refresh with mock HTTP client."""
    client = YouTubeClient(
        api_key="test_key",
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "expires_in": 3600,
    }

    with patch("src.integrations.youtube.client.async_client_context") as mock_context:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_context.return_value.__aenter__.return_value = mock_instance

        token = await client._refresh_token()

        assert token == "new_access_token"
        assert client.access_token == "new_access_token"


# YouTube Video Model Tests

def test_youtube_video_model():
    """Test YouTubeVideo model serialization."""
    video = YouTubeVideo(
        video_id="dQw4w9WgXcQ",
        title="Test Video",
        channel_title="Test Channel",
        channel_id="UC123",
        published_at=datetime.now(timezone.utc),
        thumbnail_url="https://example.com/thumb.jpg",
        description="Test description",
    )
    assert video.video_id == "dQw4w9WgXcQ"
    assert video.title == "Test Video"


def test_youtube_video_model_minimal():
    """Test YouTubeVideo model with optional fields."""
    video = YouTubeVideo(
        video_id="dQw4w9WgXcQ",
        title="Test Video",
        channel_title="Test Channel",
        channel_id="UC123",
        published_at=datetime.now(timezone.utc),
    )
    assert video.thumbnail_url is None
    assert video.description is None


# YouTube Playlist Model Tests

def test_youtube_playlist_model():
    """Test YouTubePlaylist model serialization."""
    playlist = YouTubePlaylist(
        playlist_id="PL123",
        title="Test Playlist",
        description="Test description",
        thumbnail_url="https://example.com/thumb.jpg",
        video_count=10,
        is_watch_later=False,
    )
    assert playlist.playlist_id == "PL123"
    assert playlist.video_count == 10
    assert not playlist.is_watch_later


def test_youtube_playlist_watch_later():
    """Test Watch Later playlist detection."""
    playlist = YouTubePlaylist(
        playlist_id="WL",
        title="Watch Later",
        is_watch_later=True,
    )
    assert playlist.is_watch_later


# Sync Result Model Tests

def test_sync_result_model():
    """Test SyncResult model."""
    result = SyncResult(
        ingested=5,
        skipped=2,
        errors=[{"error": "test error"}],
        duration_seconds=10.5,
    )
    assert result.ingested == 5
    assert result.skipped == 2
    assert len(result.errors) == 1


def test_sync_result_empty():
    """Test SyncResult with defaults."""
    result = SyncResult()
    assert result.ingested == 0
    assert result.skipped == 0
    assert result.errors == []
    assert result.duration_seconds == 0


# Integration Repository Tests

@pytest.mark.asyncio
async def test_integration_repo_save_tokens(db_session):
    """Test saving OAuth tokens."""
    repo = IntegrationRepository(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    token = await repo.save_tokens(
        user_id=1,
        provider="youtube",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=expires_at,
    )

    assert token.user_id == 1
    assert token.provider == "youtube"
    # Tokens are now encrypted at rest, use getter methods
    assert token.get_access_token() == "test_access_token"
    assert token.get_refresh_token() == "test_refresh_token"


@pytest.mark.asyncio
async def test_integration_repo_get_tokens(db_session):
    """Test getting OAuth tokens."""
    repo = IntegrationRepository(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Save tokens
    await repo.save_tokens(
        user_id=1,
        provider="youtube",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=expires_at,
    )

    # Get tokens
    token = await repo.get_tokens(1, "youtube")

    assert token is not None
    # Tokens are now encrypted at rest, use getter methods
    assert token.get_access_token() == "test_access_token"


@pytest.mark.asyncio
async def test_integration_repo_get_tokens_not_found(db_session):
    """Test getting non-existent tokens."""
    repo = IntegrationRepository(db_session)
    token = await repo.get_tokens(999, "youtube")
    assert token is None


@pytest.mark.asyncio
async def test_integration_repo_delete_tokens(db_session):
    """Test deleting OAuth tokens."""
    repo = IntegrationRepository(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Save tokens
    await repo.save_tokens(
        user_id=1,
        provider="youtube",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=expires_at,
    )

    # Delete tokens
    deleted = await repo.delete_tokens(1, "youtube")
    assert deleted is True

    # Verify deleted
    token = await repo.get_tokens(1, "youtube")
    assert token is None


@pytest.mark.asyncio
async def test_integration_repo_save_sync_config(db_session):
    """Test saving sync configuration."""
    repo = IntegrationRepository(db_session)

    config = await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Test Playlist",
        sync_frequency="daily",
        is_active=True,
    )

    assert config.user_id == 1
    assert config.provider == "youtube"
    assert config.resource_id == "PL123"
    assert config.resource_name == "Test Playlist"
    assert config.sync_frequency == "daily"
    assert config.is_active == 1


@pytest.mark.asyncio
async def test_integration_repo_save_sync_config_update(db_session):
    """Test updating existing sync configuration."""
    repo = IntegrationRepository(db_session)

    # Save initial config
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Original Name",
        sync_frequency="daily",
        is_active=True,
    )

    # Update config
    config = await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Updated Name",
        sync_frequency="hourly",
        is_active=False,
    )

    assert config.resource_name == "Updated Name"
    assert config.sync_frequency == "hourly"
    assert config.is_active == 0


@pytest.mark.asyncio
async def test_integration_repo_get_sync_configs(db_session):
    """Test getting sync configurations."""
    repo = IntegrationRepository(db_session)

    # Save configs
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Playlist 1",
        sync_frequency="daily",
        is_active=True,
    )

    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL456",
        playlist_name="Playlist 2",
        sync_frequency="weekly",
        is_active=True,
    )

    # Get configs
    configs = await repo.get_sync_configs(1, "youtube")

    assert len(configs) == 2
    playlist_ids = [c.playlist_id for c in configs]
    assert "PL123" in playlist_ids
    assert "PL456" in playlist_ids


@pytest.mark.asyncio
async def test_integration_repo_delete_sync_config(db_session):
    """Test deleting sync configuration."""
    repo = IntegrationRepository(db_session)

    # Save config
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Test Playlist",
        sync_frequency="daily",
        is_active=True,
    )

    # Delete config
    deleted = await repo.delete_sync_config(1, "youtube", "PL123")
    assert deleted is True

    # Verify deleted
    configs = await repo.get_sync_configs(1, "youtube")
    assert len(configs) == 0


@pytest.mark.asyncio
async def test_integration_repo_update_last_sync(db_session):
    """Test updating last sync timestamp."""
    repo = IntegrationRepository(db_session)

    # Save config
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Test Playlist",
        sync_frequency="daily",
        is_active=True,
    )

    # Update last sync
    sync_time = datetime.now(timezone.utc)
    await repo.update_last_sync(1, "youtube", "PL123", sync_time)

    # Verify
    last_sync = await repo.get_last_sync(1, "youtube", "PL123")
    assert last_sync is not None
    # Handle timezone-aware vs naive comparison (SQLite may strip timezone)
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    assert abs((last_sync - sync_time).total_seconds()) < 1


@pytest.mark.asyncio
async def test_integration_repo_log_sync(db_session):
    """Test logging sync operation."""
    repo = IntegrationRepository(db_session)

    log = await repo.log_sync(
        user_id=1,
        provider="youtube",
        resource_id="PL123",
        status="success",
        ingested_count=5,
        skipped_count=2,
        error_message=None,
    )

    assert log.user_id == 1
    assert log.provider == "youtube"
    assert log.resource_id == "PL123"
    assert log.status == "success"
    assert log.ingested_count == 5
    assert log.skipped_count == 2


@pytest.mark.asyncio
async def test_integration_repo_get_sync_logs(db_session):
    """Test getting sync logs."""
    repo = IntegrationRepository(db_session)

    # Save logs
    await repo.log_sync(
        user_id=1,
        provider="youtube",
        resource_id="PL123",
        status="success",
        ingested_count=5,
        skipped_count=2,
    )

    await repo.log_sync(
        user_id=1,
        provider="youtube",
        resource_id="PL123",
        status="partial",
        ingested_count=3,
        skipped_count=1,
        error_message="Some error",
    )

    # Get logs
    logs = await repo.get_sync_logs(1, "youtube", limit=10)

    assert len(logs) == 2
    # Most recent first
    assert logs[0].status == "partial"
    assert logs[1].status == "success"


@pytest.mark.asyncio
async def test_integration_repo_get_due_syncs(db_session):
    """Test getting sync configs due to run."""
    repo = IntegrationRepository(db_session)

    # Save hourly config (due)
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Hourly Playlist",
        sync_frequency="hourly",
        is_active=True,
    )

    # Update last sync to 2 hours ago
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    await repo.update_last_sync(1, "youtube", "PL123", old_time)

    # Save daily config (not due)
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL456",
        playlist_name="Daily Playlist",
        sync_frequency="daily",
        is_active=True,
    )

    # Update last sync to 1 hour ago
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    await repo.update_last_sync(1, "youtube", "PL456", recent_time)

    # Get due syncs
    due = await repo.get_due_syncs()

    # Only hourly should be due
    assert len(due) == 1
    assert due[0].resource_id == "PL123"


@pytest.mark.asyncio
async def test_integration_repo_get_due_syncs_never_synced(db_session):
    """Test getting sync configs that have never been synced."""
    repo = IntegrationRepository(db_session)

    # Save config without last_sync_at
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="New Playlist",
        sync_frequency="daily",
        is_active=True,
    )

    # Get due syncs
    due = await repo.get_due_syncs()

    # Should be due (never synced)
    assert len(due) == 1
    assert due[0].resource_id == "PL123"


@pytest.mark.asyncio
async def test_integration_repo_get_due_syncs_inactive(db_session):
    """Test that inactive configs are not returned as due."""
    repo = IntegrationRepository(db_session)

    # Save inactive config (would be due if active)
    await repo.save_sync_config(
        user_id=1,
        provider="youtube",
        playlist_id="PL123",
        playlist_name="Inactive Playlist",
        sync_frequency="hourly",
        is_active=False,
    )

    # Update last sync to 2 hours ago
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    await repo.update_last_sync(1, "youtube", "PL123", old_time)

    # Get due syncs
    due = await repo.get_due_syncs()

    # Should not be due (inactive)
    assert len(due) == 0


# ---------------------------------------------------------------------------
# SEC-002: OAuthState model + repository methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oauth_state_table_exists(db_session):
    """OAuthState rows can be inserted and queried."""
    from src.data.models import OAuthState
    from src.utils.datetime_utils import utc_now

    record = OAuthState(
        user_id=1,
        provider="youtube",
        state_token="test_token_abc",
        expires_at=utc_now() + timedelta(minutes=15),
    )
    db_session.add(record)
    await db_session.flush()

    assert record.id is not None
    assert record.state_token == "test_token_abc"
    assert record.created_at is not None


@pytest.mark.asyncio
async def test_save_oauth_state_returns_record(db_session):
    """save_oauth_state stores token and returns the record."""
    from src.utils.datetime_utils import utc_now

    repo = IntegrationRepository(db_session)
    expires = utc_now() + timedelta(minutes=15)
    record = await repo.save_oauth_state(
        user_id=7,
        provider="youtube",
        state_token="unique_token_xyz",
        expires_at=expires,
    )
    await db_session.flush()

    assert record.id is not None
    assert record.user_id == 7
    assert record.state_token == "unique_token_xyz"


@pytest.mark.asyncio
async def test_get_and_consume_valid_state(db_session):
    """get_and_consume_oauth_state returns user_id and deletes the row."""
    from sqlalchemy import select
    from src.data.models import OAuthState
    from src.utils.datetime_utils import utc_now

    repo = IntegrationRepository(db_session)
    await repo.save_oauth_state(
        user_id=7,
        provider="youtube",
        state_token="consume_me",
        expires_at=utc_now() + timedelta(minutes=15),
    )
    await db_session.flush()

    user_id = await repo.get_and_consume_oauth_state("consume_me", "youtube")
    assert user_id == 7

    result = await db_session.execute(
        select(OAuthState).where(OAuthState.state_token == "consume_me")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_get_and_consume_unknown_token_returns_none(db_session):
    """Unknown state token yields None."""
    repo = IntegrationRepository(db_session)
    result = await repo.get_and_consume_oauth_state("does_not_exist", "youtube")
    assert result is None


@pytest.mark.asyncio
async def test_get_and_consume_expired_token_returns_none(db_session):
    """Expired state token yields None."""
    from src.utils.datetime_utils import utc_now

    repo = IntegrationRepository(db_session)
    await repo.save_oauth_state(
        user_id=7,
        provider="youtube",
        state_token="expired_token",
        expires_at=utc_now() - timedelta(minutes=1),
    )
    await db_session.flush()

    result = await repo.get_and_consume_oauth_state("expired_token", "youtube")
    assert result is None


@pytest.mark.asyncio
async def test_get_and_consume_wrong_provider_returns_none(db_session):
    """State token scoped to wrong provider yields None."""
    from src.utils.datetime_utils import utc_now

    repo = IntegrationRepository(db_session)
    await repo.save_oauth_state(
        user_id=7,
        provider="linkedin",
        state_token="linkedin_token",
        expires_at=utc_now() + timedelta(minutes=15),
    )
    await db_session.flush()

    result = await repo.get_and_consume_oauth_state("linkedin_token", "youtube")
    assert result is None
