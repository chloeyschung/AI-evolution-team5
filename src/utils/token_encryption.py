"""Token encryption utilities for secure OAuth token storage.

TODO #1 (2026-04-14): ENCRYPTION_KEY validation moved to config.py for fail-fast behavior.
This module no longer validates ENCRYPTION_KEY at runtime - it's validated at startup in Settings.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.config import settings


class TokenEncryptionError(Exception):
    """Raised when token encryption/decryption fails."""

    pass


def _normalize_encryption_key(key: str) -> bytes:
    """Normalize encryption key to proper Fernet format.

    Fernet requires a URL-safe base64-encoded 32-byte key.
    This function handles both raw keys and pre-encoded keys.

    Args:
        key: The encryption key (raw or base64-encoded).

    Returns:
        Properly formatted Fernet key.
    """
    try:
        # Try to decode as base64 first
        decoded = base64.urlsafe_b64decode(key)
        if len(decoded) == 32:
            # Fernet expects the base64 string as bytes, not the raw decoded bytes
            return key.encode()
    except Exception:
        pass

    # If not valid base64, hash the key to get 32 bytes
    # This allows using any string as the encryption key
    sha256_hash = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash)


def _get_fernet_instance() -> Fernet:
    """Get or create Fernet instance for encryption.

    Returns:
        Fernet instance initialized with encryption key from settings.

    Raises:
        TokenEncryptionError: If ENCRYPTION_KEY format is invalid.
    """
    # ENCRYPTION_KEY is validated at startup in config.py Settings class
    encryption_key = settings.ENCRYPTION_KEY

    try:
        normalized_key = _normalize_encryption_key(encryption_key)
        return Fernet(normalized_key)
    except Exception as e:
        raise TokenEncryptionError(f"Invalid ENCRYPTION_KEY format: {e}") from e


# Create module-level Fernet instance eagerly at import time.
# ENCRYPTION_KEY is guaranteed valid by Settings at startup, so this is safe
# and eliminates any async-concurrency race on first use.
_fernet: Fernet = _get_fernet_instance()


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token for secure storage.

    Args:
        plaintext: The token to encrypt.

    Returns:
        URL-safe base64-encoded encrypted token.

    Raises:
        TokenEncryptionError: If encryption fails.
    """
    try:
        encrypted = _fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        raise TokenEncryptionError(f"Failed to encrypt token: {e}") from e


def decrypt_token(encrypted: str) -> str:
    """Decrypt a token from storage.

    Args:
        encrypted: The URL-safe base64-encoded encrypted token.

    Returns:
        The decrypted plaintext token.

    Raises:
        TokenEncryptionError: If decryption fails.
    """
    try:
        decrypted = _fernet.decrypt(encrypted.encode())
        return decrypted.decode()
    except InvalidToken as e:
        raise TokenEncryptionError(f"Invalid token format - possibly corrupted: {e}") from e
    except Exception as e:
        raise TokenEncryptionError(f"Failed to decrypt token: {e}") from e
