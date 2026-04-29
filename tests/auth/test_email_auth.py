"""Unit tests for email_auth utilities (AUTH-005)."""
import hashlib
import pytest
from src.auth.email_auth import (
    hash_password,
    verify_password,
    hmac_email,
    encrypt_email,
    decrypt_email,
    generate_token,
)


def test_hash_password_returns_string():
    assert isinstance(hash_password("mysecretpassword"), str)


def test_hash_password_is_not_plaintext():
    pw = "mysecretpassword"
    assert hash_password(pw) != pw


def test_verify_password_correct():
    pw = "mysecretpassword"
    assert verify_password(pw, hash_password(pw)) is True


def test_verify_password_wrong():
    assert verify_password("wrong", hash_password("correct")) is False


def test_hmac_email_is_deterministic():
    assert hmac_email("user@example.com") == hmac_email("user@example.com")


def test_hmac_email_normalizes_case():
    assert hmac_email("user@example.com") == hmac_email("USER@EXAMPLE.COM")


def test_hmac_email_different_addresses_differ():
    assert hmac_email("a@example.com") != hmac_email("b@example.com")


def test_encrypt_decrypt_email_roundtrip():
    email = "user@example.com"
    assert decrypt_email(encrypt_email(email)) == email


def test_encrypt_email_nondeterministic():
    email = "user@example.com"
    assert encrypt_email(email) != encrypt_email(email)


def test_generate_token_returns_raw_and_hash():
    raw, token_hash = generate_token()
    assert len(raw) > 20
    assert len(token_hash) == 64


def test_generate_token_hash_is_sha256_of_raw():
    raw, token_hash = generate_token()
    assert token_hash == hashlib.sha256(raw.encode()).hexdigest()


def test_generate_token_unique():
    raw1, _ = generate_token()
    raw2, _ = generate_token()
    assert raw1 != raw2
