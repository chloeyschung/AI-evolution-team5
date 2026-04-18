"""Integrations domain router — /integrations/youtube/* and /integrations/linkedin/*."""

import asyncio
import logging
import os
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...constants import ErrorCode, Provider
from ...data.database import get_db
from ...data.models import AuditEventType, IntegrationSyncConfig, utc_now
from ...data.repository import AuditRepository, ContentRepository
from ..dependencies import get_current_user
from ..schemas import (
    LinkedInConnectionStatus,
    LinkedInDisconnectResponse,
    LinkedInImportRequest,
    LinkedInSyncLogResponse,
    ShareResponse,
    YouTubeConnectionStatus,
    YouTubeDisconnectResponse,
    YouTubePlaylistResponse,
    YouTubeSyncConfigCreate,
    YouTubeSyncConfigResponse,
    YouTubeSyncConfigUpdate,
    YouTubeSyncLogResponse,
)

router = APIRouter()

# Background task tracking shared with app lifecycle
# These are imported from the integrations module scope so app.py can manage lifecycle
_background_tasks: set[asyncio.Task] = set()
_background_tasks_lock: asyncio.Lock = asyncio.Lock()


# INT-001: YouTube Integration endpoints


@router.get("/integrations/youtube/status", response_model=YouTubeConnectionStatus)
async def get_youtube_connection_status(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> YouTubeConnectionStatus:
    """Check YouTube connection status.

    Args:
        user_id: User ID (from auth).
        db: Database session.

    Returns:
        Connection status with last sync time.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    repo = IntegrationRepository(db)
    tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not tokens:
        return YouTubeConnectionStatus(is_connected=False)

    # Get last sync time
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)
    last_sync_at = None
    for config in configs:
        # Check database for last_sync_at
        result = await db.execute(
            select(IntegrationSyncConfig).where(
                IntegrationSyncConfig.user_id == user_id,
                IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
                IntegrationSyncConfig.resource_id == config.playlist_id,
            )
        )
        db_config = result.scalar_one_or_none()
        if db_config and db_config.last_sync_at:
            if last_sync_at is None or db_config.last_sync_at > last_sync_at:
                last_sync_at = db_config.last_sync_at

    return YouTubeConnectionStatus(
        is_connected=True,
        last_sync_at=last_sync_at.isoformat() if last_sync_at else None,
    )


@router.get("/integrations/youtube/playlists", response_model=list[YouTubePlaylistResponse])
async def list_youtube_playlists(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[YouTubePlaylistResponse]:
    """List user's YouTube playlists.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        List of YouTube playlists.

    Raises:
        401: Not connected to YouTube.
    """
    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeAuthError, YouTubeClient

    # Get YouTube tokens
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail=ErrorCode.NOT_CONNECTED_TO_YOUTUBE)

    # Create YouTube client and fetch playlists
    client = YouTubeClient(
        access_token=youtube_tokens.get_access_token(),
        refresh_token=youtube_tokens.get_refresh_token(),
        token_expires_at=youtube_tokens.expires_at,
    )

    try:
        playlists = await client.get_playlists()
    except YouTubeAuthError:
        # Token expired, delete it
        await repo.delete_tokens(user_id, Provider.YOUTUBE.value)
        raise HTTPException(status_code=401, detail=ErrorCode.YOUTUBE_AUTH_EXPIRED) from None

    return [
        YouTubePlaylistResponse(
            playlist_id=p.playlist_id,
            title=p.title,
            description=p.description,
            thumbnail_url=p.thumbnail_url,
            video_count=p.video_count,
            is_watch_later=p.is_watch_later,
        )
        for p in playlists
    ]


@router.post("/integrations/youtube/configs", status_code=201, response_model=YouTubeSyncConfigResponse)
async def create_youtube_sync_config(
    data: YouTubeSyncConfigCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> YouTubeSyncConfigResponse:
    """Create a YouTube playlist sync configuration.

    Args:
        data: Sync configuration request.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Created sync configuration.

    Raises:
        401: Not connected to YouTube.
        409: Config already exists.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Check if YouTube is connected
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail=ErrorCode.NOT_CONNECTED_TO_YOUTUBE)

    # Create sync config
    config = await repo.save_sync_config(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        playlist_id=data.playlist_id,
        playlist_name=data.playlist_name,
        sync_frequency=data.sync_frequency,
        is_active=True,
    )

    # Check if this was an update (config already exists)
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.id == config.id,
        )
    )
    db_config = result.scalar_one()

    return YouTubeSyncConfigResponse(
        playlist_id=db_config.resource_id,
        playlist_name=db_config.resource_name,
        sync_frequency=db_config.sync_frequency,
        is_active=bool(db_config.is_active),
        last_sync_at=db_config.last_sync_at.isoformat() if db_config.last_sync_at else None,
    )


@router.get("/integrations/youtube/configs", response_model=list[YouTubeSyncConfigResponse])
async def list_youtube_sync_configs(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[YouTubeSyncConfigResponse]:
    """List all YouTube sync configurations.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        List of sync configurations.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get sync configs
    repo = IntegrationRepository(db)
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)

    # Get last_sync_at from database
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
        )
    )
    db_configs = result.scalars().all()

    # Build a map for quick lookup
    db_config_map = {c.resource_id: c for c in db_configs}

    return [
        YouTubeSyncConfigResponse(
            playlist_id=c.playlist_id,
            playlist_name=c.playlist_name,
            sync_frequency=c.sync_frequency,
            is_active=c.is_active,
            last_sync_at=(
                db_config_map[c.playlist_id].last_sync_at.isoformat()
                if c.playlist_id in db_config_map and db_config_map[c.playlist_id].last_sync_at
                else None
            ),
        )
        for c in configs
    ]


@router.patch("/integrations/youtube/configs/{playlist_id}", response_model=YouTubeSyncConfigResponse)
async def update_youtube_sync_config(
    playlist_id: str,
    data: YouTubeSyncConfigUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> YouTubeSyncConfigResponse:
    """Update a YouTube sync configuration.

    Args:
        playlist_id: Playlist ID to update.
        data: Update request.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Updated sync configuration.

    Raises:
        401: Not authenticated.
        404: Config not found.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Check if config exists
    repo = IntegrationRepository(db)
    configs = await repo.get_sync_configs(user_id, Provider.YOUTUBE.value)

    existing = None
    for c in configs:
        if c.playlist_id == playlist_id:
            existing = c
            break

    if not existing:
        raise HTTPException(status_code=404, detail=ErrorCode.SYNC_CONFIG_NOT_FOUND)

    # Update config
    new_name = data.playlist_name if data.playlist_name is not None else existing.playlist_name
    new_frequency = data.sync_frequency if data.sync_frequency is not None else existing.sync_frequency
    new_active = data.is_active if data.is_active is not None else existing.is_active

    updated = await repo.save_sync_config(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        playlist_id=playlist_id,
        playlist_name=new_name,
        sync_frequency=new_frequency,
        is_active=new_active,
    )

    # Get last_sync_at from database
    result = await db.execute(
        select(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
            IntegrationSyncConfig.resource_id == playlist_id,
        )
    )
    db_config = result.scalar_one_or_none()

    return YouTubeSyncConfigResponse(
        playlist_id=updated.resource_id,
        playlist_name=updated.resource_name,
        sync_frequency=updated.sync_frequency,
        is_active=bool(updated.is_active),
        last_sync_at=db_config.last_sync_at.isoformat() if db_config and db_config.last_sync_at else None,
    )


@router.delete("/integrations/youtube/configs/{playlist_id}")
async def delete_youtube_sync_config(
    playlist_id: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a YouTube sync configuration.

    Args:
        playlist_id: Playlist ID to delete.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Deletion confirmation.

    Raises:
        401: Not authenticated.
        404: Config not found.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Check if config exists
    repo = IntegrationRepository(db)
    deleted = await repo.delete_sync_config(user_id, Provider.YOUTUBE.value, playlist_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=ErrorCode.SYNC_CONFIG_NOT_FOUND)

    return {"message": "Sync configuration deleted successfully"}


@router.get("/integrations/youtube/logs", response_model=list[YouTubeSyncLogResponse])
async def list_youtube_sync_logs(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[YouTubeSyncLogResponse]:
    """List YouTube sync logs.

    Args:
        limit: Maximum number of logs to return.
        offset: Pagination offset.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        List of sync logs.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get sync logs
    repo = IntegrationRepository(db)
    logs = await repo.get_sync_logs(user_id, Provider.YOUTUBE.value, limit=limit, offset=offset)

    return [
        YouTubeSyncLogResponse(
            id=log.id,
            playlist_id=log.playlist_id,
            status=log.status,
            ingested_count=log.ingested_count,
            skipped_count=log.skipped_count,
            error_message=log.error_message,
            executed_at=log.executed_at.isoformat(),
        )
        for log in logs
    ]


@router.post("/integrations/youtube/sync")
async def trigger_youtube_sync(
    playlist_id: str | None = None,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a YouTube playlist sync immediately.

    Args:
        playlist_id: Optional playlist ID to sync. If not provided, syncs all configured playlists.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Sync trigger confirmation.

    Raises:
        401: Not authenticated or not connected to YouTube.
    """
    from src.ai.summarizer import Summarizer
    from src.data.repository import ContentRepository
    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeClient
    from src.integrations.youtube.sync import YouTubeSyncService

    # Get YouTube tokens
    integration_repo = IntegrationRepository(db)
    youtube_tokens = await integration_repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if not youtube_tokens:
        raise HTTPException(status_code=401, detail=ErrorCode.NOT_CONNECTED_TO_YOUTUBE)

    # Create clients
    youtube_client = YouTubeClient(
        access_token=youtube_tokens.get_access_token(),
        refresh_token=youtube_tokens.get_refresh_token(),
        token_expires_at=youtube_tokens.expires_at,
    )

    content_repo = ContentRepository(db)

    # Initialize summarizer with API key
    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not summarizer_api_key:
        raise HTTPException(status_code=500, detail="anthropic_api_key_not_configured")

    summarizer = Summarizer(api_key=summarizer_api_key)
    sync_service = YouTubeSyncService(
        youtube_client=youtube_client,
        content_repo=content_repo,
        integration_repo=integration_repo,
        summarizer=summarizer,
    )

    # Trigger sync (run in background to avoid blocking)
    async def do_sync():
        try:
            if playlist_id:
                result = await sync_service.sync_playlist(user_id, playlist_id)
                status = "success" if not result.errors else "partial"
                await integration_repo.log_sync(
                    user_id=user_id,
                    provider=Provider.YOUTUBE.value,
                    resource_id=playlist_id,
                    status=status,
                    ingested_count=result.ingested,
                    skipped_count=result.skipped,
                    error_message=None if not result.errors else str(result.errors),
                )
                await db.commit()  # Ensure sync log is persisted
            else:
                results = await sync_service.sync_all_playlists(user_id)
                for pid, result in results.items():
                    status = "success" if not result.errors else "partial"
                    await integration_repo.log_sync(
                        user_id=user_id,
                        provider=Provider.YOUTUBE.value,
                        resource_id=pid,
                        status=status,
                        ingested_count=result.ingested,
                        skipped_count=result.skipped,
                        error_message=None if not result.errors else str(result.errors),
                    )
                    await db.commit()  # Ensure sync log is persisted
        except Exception as e:
            resource = playlist_id or "all"
            await integration_repo.log_sync(
                user_id=user_id,
                provider=Provider.YOUTUBE.value,
                resource_id=resource,
                status="failed",
                ingested_count=0,
                skipped_count=0,
                error_message=str(e),
            )
            await db.commit()  # Ensure error log is persisted

    # Schedule background task with exception handling and tracking
    async def background_task_wrapper():
        """Wrapper to ensure exceptions don't crash the process.

        TODO #2 (2026-04-14): Uses _background_tasks_lock for thread-safe task management.
        """
        current_task = asyncio.current_task()
        try:
            logging.info("YouTube sync background task started")
            await do_sync()
            logging.info("YouTube sync background task completed")
        except Exception as e:
            # Log unhandled exceptions (should not happen due to do_sync try/except)
            logging.error(f"Uncaught exception in YouTube sync background task: {e}")
        finally:
            # TODO #2 (2026-04-14): Thread-safe task removal using lock
            if current_task:
                async with _background_tasks_lock:
                    _background_tasks.discard(current_task)

    task = asyncio.create_task(background_task_wrapper())
    # TODO #2 (2026-04-14): Thread-safe task addition using lock
    async with _background_tasks_lock:
        _background_tasks.add(task)
    logging.info(f"YouTube sync background task scheduled (task id: {id(task)})")

    return {
        "message": "Sync triggered",
        "playlist_id": playlist_id,
    }


@router.post("/integrations/youtube/connect")
async def connect_youtube(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate YouTube OAuth connection.

    Returns OAuth authorization URL for user to complete consent flow.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        OAuth authorization URL.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail=ErrorCode.YOUTUBE_OAUTH_NOT_CONFIGURED)

    # Build OAuth URL
    scope = "https://www.googleapis.com/auth/youtube.readonly"
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/youtube/callback")

    # Generate cryptographically random CSRF state token and store server-side (SEC-002)
    state_token = secrets.token_urlsafe(16)
    repo = IntegrationRepository(db)
    await repo.save_oauth_state(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        state_token=state_token,
        expires_at=utc_now() + timedelta(minutes=15),
    )

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state_token,
        }
    )

    return {"auth_url": auth_url}


@router.get("/integrations/youtube/callback")
async def youtube_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle YouTube OAuth callback.

    Exchanges authorization code for tokens and stores them.

    Args:
        code: Authorization code from YouTube.
        state: CSRF state token (issued by connect endpoint, single-use).
        db: Database session.

    Returns:
        Connection confirmation.

    Raises:
        400: Invalid code or state.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Validate and consume CSRF state token — derives user_id from server-side record (SEC-002)
    repo = IntegrationRepository(db)
    user_id = await repo.get_and_consume_oauth_state(state, Provider.YOUTUBE.value)
    if user_id is None:
        raise HTTPException(status_code=400, detail=ErrorCode.INVALID_STATE)

    # Get OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail=ErrorCode.YOUTUBE_OAUTH_NOT_CONFIGURED)

    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/youtube/callback")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=ErrorCode.YOUTUBE_AUTH_FAILED)

    token_data = response.json()

    # Store tokens
    expires_at = utc_now() + timedelta(seconds=token_data.get("expires_in", 3600))

    await repo.save_tokens(
        user_id=user_id,
        provider=Provider.YOUTUBE.value,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
    )

    ip = request.client.host if request.client else None
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.OAUTH_CONNECT,
        user_id=user_id,
        ip_address=ip,
        metadata={"provider": "youtube"},
    )
    await db.commit()

    return {
        "message": "Connected to YouTube successfully",
        "user_id": user_id,
    }


@router.post("/integrations/youtube/disconnect")
async def disconnect_youtube(
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> YouTubeDisconnectResponse:
    """Disconnect YouTube integration.

    Revokes OAuth tokens and deletes all sync configurations.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Disconnection confirmation.

    Raises:
        401: Not authenticated.
    """

    from src.integrations.repositories.integration import IntegrationRepository
    from src.integrations.youtube.client import YouTubeClient

    # Get YouTube tokens
    repo = IntegrationRepository(db)
    youtube_tokens = await repo.get_tokens(user_id, Provider.YOUTUBE.value)

    if youtube_tokens:
        # Revoke tokens with YouTube
        client = YouTubeClient(
            access_token=youtube_tokens.get_access_token(),
            refresh_token=youtube_tokens.get_refresh_token(),
            token_expires_at=youtube_tokens.expires_at,
        )
        await client.disconnect()

        # Delete tokens from database
        await repo.delete_tokens(user_id, Provider.YOUTUBE.value)

    # Delete all sync configs
    await db.execute(
        delete(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.YOUTUBE.value,
        )
    )

    ip = request.client.host if request.client else None
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.OAUTH_DISCONNECT,
        user_id=user_id,
        ip_address=ip,
        metadata={"provider": "youtube"},
    )
    await db.commit()

    return YouTubeDisconnectResponse(message="Disconnected from YouTube successfully")


# INT-002: LinkedIn Integration endpoints


@router.get("/integrations/linkedin/status", response_model=LinkedInConnectionStatus)
async def get_linkedin_status(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkedInConnectionStatus:
    """Get LinkedIn connection status.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        LinkedIn connection status.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Check if LinkedIn tokens exist
    repo = IntegrationRepository(db)
    tokens = await repo.get_tokens(user_id, Provider.LINKEDIN.value)

    if not tokens:
        return LinkedInConnectionStatus(is_connected=False)

    # Get last sync time
    last_sync = await repo.get_last_sync(user_id, Provider.LINKEDIN.value, "saved_posts")

    return LinkedInConnectionStatus(
        is_connected=True,
        last_sync_at=last_sync.isoformat() if last_sync else None,
    )


@router.post("/integrations/linkedin/disconnect", response_model=LinkedInDisconnectResponse)
async def disconnect_linkedin(
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkedInDisconnectResponse:
    """Disconnect LinkedIn integration.

    Revokes OAuth tokens and deletes all sync configurations.

    Args:
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        Disconnection confirmation.

    Raises:
        401: Not authenticated.
    """

    from src.integrations.repositories.integration import IntegrationRepository

    # Delete tokens from database
    repo = IntegrationRepository(db)
    await repo.delete_tokens(user_id, Provider.LINKEDIN.value)

    # Delete all sync configs
    await db.execute(
        delete(IntegrationSyncConfig).where(
            IntegrationSyncConfig.user_id == user_id,
            IntegrationSyncConfig.provider == Provider.LINKEDIN.value,
        )
    )

    ip = request.client.host if request.client else None
    audit = AuditRepository(db)
    await audit.log_event(
        AuditEventType.OAUTH_DISCONNECT,
        user_id=user_id,
        ip_address=ip,
        metadata={"provider": "linkedin"},
    )
    await db.commit()

    return LinkedInDisconnectResponse(message="Disconnected from LinkedIn successfully")


@router.get("/integrations/linkedin/sync/logs", response_model=list[LinkedInSyncLogResponse])
async def get_linkedin_sync_logs(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LinkedInSyncLogResponse]:
    """Get LinkedIn sync logs.

    Args:
        limit: Maximum number of logs to return.
        offset: Offset for pagination.
        user_id: Current user ID from authentication.
        db: Database session.

    Returns:
        List of sync logs.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.repositories.integration import IntegrationRepository

    # Get sync logs
    repo = IntegrationRepository(db)
    logs = await repo.get_sync_logs(user_id, Provider.LINKEDIN.value, limit=limit, offset=offset)

    return [
        LinkedInSyncLogResponse(
            id=log.id,
            resource_id=log.resource_id,
            status=log.status,
            ingested_count=log.ingested_count,
            skipped_count=log.skipped_count,
            error_message=log.error_message,
            executed_at=log.executed_at.isoformat(),
        )
        for log in logs
    ]


@router.post("/integrations/linkedin/import", status_code=201, response_model=ShareResponse)
async def import_linkedin_post(
    data: LinkedInImportRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Import a single LinkedIn post by URL.

    This endpoint allows manual import of LinkedIn posts without OAuth.
    It fetches the post data from the public URL.

    Args:
        data: Import request with LinkedIn post URL.
        user_id: Current user ID (from auth).
        db: Database session.

    Returns:
        Share response with imported content.

    Raises:
        401: Not authenticated.
    """
    from src.integrations.linkedin.client import LinkedInClient
    from src.integrations.linkedin.sync import LinkedInSyncService

    # Create LinkedIn client (no auth needed for public posts)
    client = LinkedInClient(access_token="")

    # Use sync service to import the post
    result = await LinkedInSyncService(db).sync_single_post(
        user_id=user_id,
        url=data.url,
        client=client,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", ErrorCode.FAILED_TO_IMPORT))

    # Fetch the content for response
    content_id = result.get("content_id")
    if not content_id:
        raise HTTPException(status_code=500, detail=ErrorCode.FAILED_TO_GET_CONTENT_ID)

    content_repo = ContentRepository(db)
    content = await content_repo.get_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail=ErrorCode.CONTENT_NOT_FOUND)

    return ShareResponse(
        id=content.id,
        platform=content.platform,
        content_type=content.content_type,
        url=content.url,
        title=content.title,
        author=content.author,
        summary=content.summary,
        created_at=content.created_at.isoformat(),
    )
