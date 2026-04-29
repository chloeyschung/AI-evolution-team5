"""Sign in with Apple identity-token verification."""

import json
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


class AppleTokenVerificationError(Exception):
    """Raised when an Apple identity token cannot be verified."""


async def verify_apple_identity_token(identity_token: str, bundle_id: str) -> dict[str, Any]:
    """Verify an Apple identity token and return its claims."""
    try:
        header = jwt.get_unverified_header(identity_token)
    except jwt.InvalidTokenError as exc:
        raise AppleTokenVerificationError("Invalid Apple identity token header.") from exc

    key_id = header.get("kid")
    if not key_id:
        raise AppleTokenVerificationError("Apple identity token is missing key id.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(APPLE_KEYS_URL)
        response.raise_for_status()
        jwks = response.json()

    key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == key_id), None)
    if key_data is None:
        raise AppleTokenVerificationError("Apple signing key not found.")

    try:
        public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
        claims = jwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=bundle_id,
            issuer=APPLE_ISSUER,
        )
    except (jwt.InvalidTokenError, httpx.HTTPError) as exc:
        raise AppleTokenVerificationError("Invalid Apple identity token.") from exc

    if not claims.get("sub"):
        raise AppleTokenVerificationError("Apple identity token is missing subject.")

    return claims
