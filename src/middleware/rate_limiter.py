"""Rate limiting middleware for Briefly API."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter with default error handler
limiter = Limiter(
    key_func=get_remote_address,
    default_errors={
        429: {"detail": "Rate limit exceeded. Please try again later."}
    }
)


def rate_limit_exceeded_handler(request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors.

    Args:
        request: The FastAPI request object.
        exc: The RateLimitExceeded exception.

    Returns:
        JSONResponse with 429 status code.
    """
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )
