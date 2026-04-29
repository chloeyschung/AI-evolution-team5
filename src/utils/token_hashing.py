"""Token hashing utilities for secure JWT storage."""

import hashlib


def hash_access_token(token: str) -> str:
    """Hash an access token for secure storage.

    Uses SHA-256 to hash the token. The hash is stored instead of the
    plaintext token to protect against database compromise.

    Args:
        token: The JWT access token to hash.

    Returns:
        Hex-encoded SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_access_token(stored_hash: str, token: str) -> bool:
    """Verify an access token against its stored hash.

    Args:
        stored_hash: The hash stored in the database.
        token: The JWT access token to verify.

    Returns:
        True if the token matches the stored hash, False otherwise.
    """
    return hashlib.sha256(token.encode()).hexdigest() == stored_hash
