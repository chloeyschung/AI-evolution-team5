#!/usr/bin/env python
"""Migrate existing UserProfile.google_sub rows to user_auth_methods (AUTH-005).

Run once after deploying new models:
    uv run python scripts/migrate_google_sub.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.constants import AuthProvider
from src.data.models import Base, UserProfile, UserAuthMethod
from src.utils.datetime_utils import utc_now

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./briefly.db")


async def run():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.google_sub.isnot(None))
        )
        users = result.scalars().all()
        migrated = skipped = 0

        for user in users:
            existing = await session.execute(
                select(UserAuthMethod).where(
                    UserAuthMethod.provider == AuthProvider.GOOGLE,
                    UserAuthMethod.provider_id == user.google_sub,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            session.add(UserAuthMethod(
                user_id=user.id,
                provider=AuthProvider.GOOGLE,
                provider_id=user.google_sub,
                email_verified=True,
                verified_at=user.created_at,
            ))
            migrated += 1

        await session.commit()
        print(f"Migration complete: {migrated} migrated, {skipped} already existed.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
