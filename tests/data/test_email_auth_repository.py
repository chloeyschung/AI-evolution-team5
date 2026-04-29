"""Integration tests for EmailAuthRepository (AUTH-005)."""
import pytest
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import AuthProvider
from src.data.email_auth_repository import EmailAuthRepository
from src.data.models import UserProfile
from src.utils.datetime_utils import utc_now


@pytest.fixture
async def user(db_session: AsyncSession) -> UserProfile:
    u = UserProfile(email="repo-test@example.com", created_at=utc_now(), updated_at=utc_now())
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
def repo(db_session: AsyncSession) -> EmailAuthRepository:
    return EmailAuthRepository(db_session)


async def test_create_and_get_auth_method(user, repo):
    method = await repo.create_auth_method(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id="hmac-of-email",
        password_hash="argon2hash",
        email_encrypted="fernet-encrypted",
    )
    assert method.id is not None
    found = await repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, "hmac-of-email")
    assert found is not None and found.user_id == user.id


async def test_get_auth_method_not_found(repo):
    assert await repo.get_auth_method_by_provider(AuthProvider.GOOGLE, "nonexistent") is None


async def test_get_auth_methods_for_user(user, repo):
    await repo.create_auth_method(user.id, AuthProvider.GOOGLE, "gsub123")
    await repo.create_auth_method(user.id, AuthProvider.EMAIL_PASSWORD, "hmac456", password_hash="h")
    assert len(await repo.get_auth_methods_for_user(user.id)) == 2


async def test_mark_email_verified(user, repo):
    method = await repo.create_auth_method(user.id, AuthProvider.EMAIL_PASSWORD, "hmac789")
    updated = await repo.mark_email_verified(method.id)
    assert updated.email_verified is True and updated.verified_at is not None


async def test_create_and_consume_verification_token(user, repo):
    await repo.create_verification_token(user.id, "abc123hash", utc_now() + timedelta(hours=24))
    consumed = await repo.consume_verification_token("abc123hash")
    assert consumed is not None and consumed.used_at is not None
    assert await repo.consume_verification_token("abc123hash") is None


async def test_invalidate_all_verification_tokens_for_user(user, repo):
    await repo.create_verification_token(user.id, "hash1", utc_now() + timedelta(hours=24))
    await repo.create_verification_token(user.id, "hash2", utc_now() + timedelta(hours=24))

    invalidated = await repo.invalidate_verification_tokens_for_user(user.id)

    assert invalidated == 2
    assert await repo.consume_verification_token("hash1") is None
    assert await repo.consume_verification_token("hash2") is None


async def test_expired_verification_token_returns_none(user, repo):
    await repo.create_verification_token(user.id, "expiredhash", utc_now() - timedelta(hours=1))
    assert await repo.consume_verification_token("expiredhash") is None


async def test_create_and_consume_reset_token(user, repo):
    await repo.create_reset_token(user.id, "resethash123", utc_now() + timedelta(hours=1))
    consumed = await repo.consume_reset_token("resethash123")
    assert consumed is not None and consumed.user_id == user.id
    assert await repo.consume_reset_token("resethash123") is None


async def test_update_password(user, repo):
    method = await repo.create_auth_method(user.id, AuthProvider.EMAIL_PASSWORD, "hmacxxx", password_hash="old")
    updated = await repo.update_password(method.id, "newhash")
    assert updated.password_hash == "newhash"
