"""Token encryption utilities for secure OAuth token storage."""

import base64
import hashlib
import os
from cryptography.fernet import Fernet, InvalidToken


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
            return decoded
    except Exception:
        pass

    # If not valid base64, hash the key to get 32 bytes
    # This allows using any string as the encryption key
    sha256_hash = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash)


def _get_fernet_instance() -> Fernet:
    """Get or create Fernet instance for encryption.

    Returns:
        Fernet instance initialized with encryption key.

    Raises:
        TokenEncryptionError: If ENCRYPTION_KEY is not set.
    """
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise TokenEncryptionError(
            "ENCRYPTION_KEY environment variable is required for token encryption"
        )

    try:
        normalized_key = _normalize_encryption_key(encryption_key)
        return Fernet(normalized_key)
    except Exception as e:
        raise TokenEncryptionError(f"Invalid ENCRYPTION_KEY format: {e}") from e


# Create module-level Fernet instance (lazy initialization)
_fernet: Fernet | None = None


def _get_or_create_fernet() -> Fernet:
    """Get or create the Fernet instance.

    Returns:
        Fernet instance.
    """
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet_instance()
    return _fernet


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
        fernet = _get_or_create_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
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
        fernet = _get_or_create_fernet()
        decrypted = fernet.decrypt(encrypted.encode())
        return decrypted.decode()
    except InvalidToken as e:
        raise TokenEncryptionError(f"Invalid token format - possibly corrupted: {e}") from e
    except Exception as e:
        raise TokenEncryptionError(f"Failed to decrypt token: {e}") from e
