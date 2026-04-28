"""Database connection and session management."""

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

from .models import Base

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=os.getenv("DB_ECHO", "false").lower() == "true")
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes.

    Yields an async database session for use in API routes.
    Session is automatically committed on success, rolled back on error,
    and always closed properly.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_user_profile_timezone_column(conn)
        await _ensure_content_ai_columns(conn)


async def _ensure_user_profile_timezone_column(conn) -> None:
    """Backfill schema drift for existing SQLite DBs.

    `create_all()` does not alter existing tables. If `user_profile` was created
    before the `timezone` column existed, add it at startup to keep API responses
    compatible with profile schema expectations.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    result = await conn.execute(text("PRAGMA table_info(user_profile)"))
    existing_columns = {row[1] for row in result.fetchall()}
    if "timezone" in existing_columns:
        return

    await conn.execute(
        text("ALTER TABLE user_profile ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC'")
    )


async def _ensure_content_ai_columns(conn) -> None:
    """Backfill content schema drift for AI flags and duplicate indexing columns."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    result = await conn.execute(text("PRAGMA table_info(content)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "is_ai_summarized" not in existing_columns:
        await conn.execute(
            text("ALTER TABLE content ADD COLUMN is_ai_summarized BOOLEAN NOT NULL DEFAULT 0")
        )
    if "is_ai_titled" not in existing_columns:
        await conn.execute(
            text("ALTER TABLE content ADD COLUMN is_ai_titled BOOLEAN NOT NULL DEFAULT 0")
        )
    if "duplicate_group_key" not in existing_columns:
        await conn.execute(
            text("ALTER TABLE content ADD COLUMN duplicate_group_key VARCHAR(1024)")
        )
    if "duplicate_index" not in existing_columns:
        await conn.execute(
            text("ALTER TABLE content ADD COLUMN duplicate_index INTEGER")
        )
