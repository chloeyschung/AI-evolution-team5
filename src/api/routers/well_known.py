"""Well-known endpoints required for iOS Universal Links and App Store compliance."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

# iOS Universal Links: Apple App Site Association (AASA)
# Must be served at exactly /.well-known/apple-app-site-association (no .json extension).
# iOS requires Content-Type: application/json (NOT application/octet-stream).
# Placeholder TEAMID and bundle ID — fill in before App Store submission.
_AASA_PAYLOAD = {
    "applinks": {
        "apps": [],
        "details": [
            {
                "appID": "TEAMID.com.briefly.app",
                "paths": ["*"],
            }
        ],
    }
}


@router.get(
    "/.well-known/apple-app-site-association",
    include_in_schema=False,
)
async def apple_app_site_association() -> JSONResponse:
    """Serve the Apple App Site Association file for iOS Universal Links.

    iOS fetches this URL during app installation to verify the domain association.
    The response must use Content-Type: application/json; iOS rejects
    application/octet-stream even though Apple's own CDN sometimes serves it that way.
    """
    return JSONResponse(content=_AASA_PAYLOAD, media_type="application/json")
