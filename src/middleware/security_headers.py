"""Security headers middleware for Briefly API.

Implements SEC-001 security requirements:
- X-Content-Type-Options: nosniff (prevent MIME type sniffing)
- X-Frame-Options: DENY (prevent clickjacking)
- X-XSS-Protection: 1; mode=block (enable XSS filter)
"""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Increment this when making breaking API changes — iOS clients check X-API-Version to detect deploys
_API_VERSION = "1"


def _apply_security_headers(response: Response) -> Response:
    """Attach SEC-001 headers to a response object."""
    # Prevent MIME type sniffing (browsers won't guess content type)
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking (page cannot be embedded in frames)
    # SEC-001 requirement (line 70)
    response.headers["X-Frame-Options"] = "DENY"

    # Enable XSS filter in legacy browsers (Chrome, Safari)
    # SEC-001 requirement (line 71)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Prevent IE from downloading files as attachments
    response.headers["X-Download-Options"] = "noopen"

    # Block cross-domain policies (Flash, JavaApplets)
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    # Enforce HTTPS for 1 year, including subdomains
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Let iOS clients detect breaking API changes after OTA backend deploys
    response.headers["X-API-Version"] = _API_VERSION

    return response


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses.

    This middleware implements the security headers specified in SEC-001.
    It wraps every response and adds protective headers to prevent common
    web vulnerabilities.

    Starlette's BaseHTTPMiddleware re-raises exceptions that leak from
    call_next, bypassing FastAPI's exception handlers.  We catch unhandled
    exceptions here so they always return a structured JSON 500 rather than
    letting the exception propagate to the ASGI server.

    Args:
        request: The incoming HTTP request
        call_next: The next handler in the middleware chain

    Returns:
        The response with security headers added
    """
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception in request %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        response = JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "message": "An unexpected error occurred.", "code": 500},
        )
        return _apply_security_headers(response)

    return _apply_security_headers(response)
