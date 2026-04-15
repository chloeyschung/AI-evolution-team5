"""Security headers middleware for Briefly API.

Implements SEC-001 security requirements:
- X-Content-Type-Options: nosniff (prevent MIME type sniffing)
- X-Frame-Options: DENY (prevent clickjacking)
- X-XSS-Protection: 1; mode=block (enable XSS filter)
"""

from fastapi import Request, Response


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses.

    This middleware implements the security headers specified in SEC-001.
    It wraps every response and adds protective headers to prevent common
    web vulnerabilities.

    Args:
        request: The incoming HTTP request
        call_next: The next handler in the middleware chain

    Returns:
        The response with security headers added
    """
    response = await call_next(request)

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

    return response
