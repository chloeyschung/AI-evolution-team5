"""Google OAuth utilities for authentication.

Provides Google ID token verification and user info extraction.
"""

import httpx
from typing import Optional, Dict, Any

from src.utils.http_client import async_client_context


# Google OAuth configuration
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthError(Exception):
    """Base exception for Google OAuth errors."""
    pass


class GoogleTokenVerificationError(GoogleOAuthError):
    """Raised when Google ID token verification fails."""
    pass


class GoogleUserInfoError(GoogleOAuthError):
    """Raised when fetching Google user info fails."""
    pass


async def verify_google_id_token(id_token: str, client_id: str | None = None) -> Dict[str, Any]:
    """Verify Google ID token and return decoded claims.

    Args:
        id_token: Google ID token from the client
        client_id: Optional client ID to verify against (audience claim)

    Returns:
        Dictionary with decoded token claims (sub, email, etc.)

    Raises:
        GoogleTokenVerificationError: If token is invalid or verification fails
    """
    params = {"id_token": id_token}
    if client_id:
        params["audience"] = client_id

    try:
        async with async_client_context() as client:
            response = await client.get(GOOGLE_TOKEN_INFO_URL, params=params, timeout=10.0)

            if response.status_code != 200:
                raise GoogleTokenVerificationError(
                    f"Google token verification failed: {response.status_code}"
                )

            token_info = response.json()

            # Check for error in response
            if "error" in token_info:
                raise GoogleTokenVerificationError(
                    f"Google token verification error: {token_info['error']}"
                )

            return token_info

    except httpx.HTTPError as e:
        raise GoogleTokenVerificationError(f"Failed to verify Google token: {e}")
    except ValueError as e:
        raise GoogleTokenVerificationError(f"Invalid Google token response: {e}")


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """Fetch user info from Google using access token.

    Args:
        access_token: Google access token

    Returns:
        Dictionary with user info (id, email, name, picture, etc.)

    Raises:
        GoogleUserInfoError: If fetching user info fails
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with async_client_context() as client:
            response = await client.get(GOOGLE_USER_INFO_URL, headers=headers, timeout=10.0)

            if response.status_code != 200:
                raise GoogleUserInfoError(
                    f"Google user info fetch failed: {response.status_code}"
                )

            return response.json()

    except httpx.HTTPError as e:
        raise GoogleUserInfoError(f"Failed to fetch Google user info: {e}")
    except ValueError as e:
        raise GoogleUserInfoError(f"Invalid Google user info response: {e}")


def extract_user_info_from_token(token_info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract user info from verified Google token info.

    Args:
        token_info: Verified Google token info from verify_google_id_token

    Returns:
        Dictionary with extracted user info:
        - google_sub: Google user ID (sub claim)
        - email: User email
        - email_verified: Whether email is verified
        - name: Display name (if available)
        - picture: Profile picture URL (if available)
    """
    return {
        "google_sub": token_info.get("sub"),
        "email": token_info.get("email"),
        "email_verified": token_info.get("email_verified", False),
        "name": token_info.get("name"),
        "picture": token_info.get("picture"),
        "given_name": token_info.get("given_name"),
        "family_name": token_info.get("family_name"),
    }
