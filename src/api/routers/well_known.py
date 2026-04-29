"""Well-known endpoints required for iOS Universal Links and App Store compliance."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...config import settings

router = APIRouter()


@router.get(
    "/.well-known/apple-app-site-association",
    include_in_schema=False,
)
async def apple_app_site_association() -> JSONResponse:
    """Serve the Apple App Site Association file for iOS Universal Links.

    iOS fetches this URL during app installation to verify the domain association.
    The response must use Content-Type: application/json; iOS rejects
    application/octet-stream even though Apple's own CDN sometimes serves it that way.

    Requires APPLE_TEAM_ID to be set in the environment. Returns 503 until configured.
    See docs/ios-universal-links.md for setup instructions.
    """
    if not settings.APPLE_TEAM_ID:
        return JSONResponse(
            status_code=503,
            content={
                "error": "not_configured",
                "message": "APPLE_TEAM_ID is not set. See docs/ios-universal-links.md.",
            },
        )

    payload = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": f"{settings.APPLE_TEAM_ID}.{settings.APPLE_BUNDLE_ID}",
                    "paths": ["*"],
                }
            ],
        }
    }
    return JSONResponse(content=payload, media_type="application/json")
