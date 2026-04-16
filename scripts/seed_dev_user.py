#!/usr/bin/env python
"""Seed a pre-verified dev user for local testing (AUTH-005).

Usage:
    uv run python scripts/seed_dev_user.py

Creates: test@localhost / testpass123 — pre-verified, no email step needed.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.data.models import Base, UserProfile
from src.utils.datetime_utils import utc_now

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///briefly.db")
DEV_EMAIL = "test@localhost"
DEV_PASSWORD = "testpass123"


async def run():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        existing = await session.execute(
            select(UserProfile).where(UserProfile.email == DEV_EMAIL)
        )
        if existing.scalar_one_or_none():
            print(f"Dev user already exists: {DEV_EMAIL}")
            await engine.dispose()
            return

        from tests.factories import make_user
        user, token = await make_user(session, email=DEV_EMAIL, password=DEV_PASSWORD)
        print("Dev user created:")
        print(f"  Email:    {DEV_EMAIL}")
        print(f"  Password: {DEV_PASSWORD}")
        print(f"  User ID:  {user.id}")
        print(f"  Token:    {token[:20]}...")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
