"""Email/password authentication utilities (AUTH-005).

Provides credential hashing, email encryption, and token generation for
the email_password auth provider.
"""
import hashlib
import hmac as _hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.config import settings
from src.utils.token_encryption import encrypt_token, decrypt_token

# Argon2id parameters — OWASP minimum for interactive login
_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(plaintext: str) -> str:
    """Hash a password with Argon2id."""
    return _ph.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _ph.verify(hashed, plaintext)
    except VerifyMismatchError:
        return False


def hmac_email(email: str) -> str:
    """HMAC-SHA256 of normalized email for deterministic DB lookup.

    Keyed with EMAIL_LOOKUP_KEY — safe to use as UNIQUE index.
    Returns 64-char hex digest.
    """
    normalized = email.strip().lower()
    key = settings.EMAIL_LOOKUP_KEY.encode()
    return _hmac.new(key, normalized.encode(), hashlib.sha256).hexdigest()


def encrypt_email(email: str) -> str:
    """Fernet-encrypt an email address for at-rest storage.

    Non-deterministic. Use hmac_email() for lookup; this for storage.
    """
    return encrypt_token(email)


def decrypt_email(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted email address."""
    return decrypt_token(encrypted)


def generate_token() -> tuple[str, str]:
    """Generate a cryptographically secure single-use token.

    Returns:
        (raw_token, sha256_hex_hash) — send raw in email, store only hash.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()
