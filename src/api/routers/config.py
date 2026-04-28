"""App lifecycle and configuration endpoint for iOS clients."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...config import settings
from ..schemas import AppConfigResponse

router = APIRouter()


@router.get("/config/app", response_model=AppConfigResponse)
async def get_app_config() -> AppConfigResponse:
    """Return app lifecycle configuration for iOS clients.

    iOS clients should check this at app launch to handle:
    - Force updates (min_version / min_ios_version)
    - Maintenance mode (is_maintenance + maintenance_message)
    - Store redirect URL (store_url)
    """
    return AppConfigResponse(
        min_version=settings.MIN_APP_VERSION,
        min_ios_version=settings.MIN_IOS_VERSION,
        is_maintenance=settings.MAINTENANCE_MODE,
        maintenance_message=settings.MAINTENANCE_MESSAGE or None,
        store_url=settings.STORE_URL or None,
    )
