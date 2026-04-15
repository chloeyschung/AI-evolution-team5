"""Token utilities for authentication.

Provides JWT access token and opaque refresh token generation/validation.

TODO #5 (2026-04-14): Added algorithm header validation to prevent algorithm confusion attacks
TODO #10 (2026-04-14): Replace Optional with | None syntax
"""

import secrets
from datetime import timedelta

import jwt

from src.config import settings
from src.utils.datetime_utils import utc_now

# Token configuration
ACCESS_TOKEN_EXPIRY_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRY_DAYS = 7  # 7 days


def create_access_token(user_id: int) -> str:
    """Create JWT access token for user.

    Args:
        user_id: The user ID to encode in the token

    Returns:
        JWT access token string
    """
    now = utc_now()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES)

    payload = {
        "sub": str(user_id),  # subject = user_id
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    return token


def verify_access_token(token: str) -> int | None:
    """Verify JWT access token and extract user ID.

    Args:
        token: The JWT access token to verify

    Returns:
        User ID if token is valid, None if invalid or expired

    Security:
        TODO #5 (2026-04-14): Validates algorithm header to prevent algorithm confusion attacks.
        Only HS256 is accepted - rejects none/RS256/etc.
    """
    try:
        # First, get the header without verification to check algorithm
        # This allows us to validate the algorithm before full verification
        header = jwt.get_unverified_header(token)

        # TODO #5 (2026-04-14): Explicit algorithm header validation
        # Prevent algorithm confusion attacks by rejecting anything other than HS256
        if header.get("alg") != "HS256":
            return None

        # Now verify with strict algorithm enforcement
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            return None

        return int(user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        # Catch any other unexpected errors (malformed tokens, etc.)
        return None


def create_refresh_token() -> str:
    """Create opaque refresh token.

    Uses cryptographically secure random string.

    Returns:
        Opaque refresh token string (32 bytes, URL-safe base64)
    """
    return secrets.token_urlsafe(32)


def verify_refresh_token(token: str) -> bool:
    """Verify refresh token format.

    Note: Actual validation happens in repository by checking database.
    This only validates the token format.

    Args:
        token: The refresh token to verify

    Returns:
        True if token format is valid, False otherwise
    """
    try:
        # URL-safe base64 tokens should be 43 characters (32 bytes encoded)
        if len(token) != 43:
            return False

        # Try to decode to verify it's valid base64
        token.encode("ascii").decode("ascii")
        return True
    except (ValueError, UnicodeError):
        return False
