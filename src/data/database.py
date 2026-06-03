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
        await _ensure_content_auto_tag_columns(conn)
        await _ensure_content_reflection_columns(conn)
        await _ensure_content_memo_column(conn)


async def _ensure_user_profile_timezone_column(conn) -> None:
    """Backfill schema drift: add timezone column to user_profile if missing."""
    if DATABASE_URL.startswith("sqlite"):
        result = await conn.execute(text("PRAGMA table_info(user_profile)"))
        if "timezone" in {row[1] for row in result.fetchall()}:
            return
        await conn.execute(text("ALTER TABLE user_profile ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC'"))
    else:
        await conn.execute(text("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC'"))


async def _ensure_content_ai_columns(conn) -> None:
    """Backfill content schema drift for AI flags and duplicate indexing columns."""
    if DATABASE_URL.startswith("sqlite"):
        result = await conn.execute(text("PRAGMA table_info(content)"))
        existing_columns = {row[1] for row in result.fetchall()}
        if "is_ai_summarized" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN is_ai_summarized BOOLEAN NOT NULL DEFAULT 0"))
        if "is_ai_titled" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN is_ai_titled BOOLEAN NOT NULL DEFAULT 0"))
        if "duplicate_group_key" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN duplicate_group_key VARCHAR(1024)"))
        if "duplicate_index" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN duplicate_index INTEGER"))
    else:
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS is_ai_summarized BOOLEAN NOT NULL DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS is_ai_titled BOOLEAN NOT NULL DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS duplicate_group_key VARCHAR(1024)"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS duplicate_index INTEGER"))


async def _ensure_content_auto_tag_columns(conn) -> None:
    """Backfill auto-tag columns added for Gemini auto-tagging feature."""
    if DATABASE_URL.startswith("sqlite"):
        result = await conn.execute(text("PRAGMA table_info(content)"))
        existing_columns = {row[1] for row in result.fetchall()}
        if "auto_tag_status" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN auto_tag_status VARCHAR(20)"))
        if "auto_tag_category" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN auto_tag_category VARCHAR(50)"))
        if "auto_tag_keywords_en" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN auto_tag_keywords_en TEXT"))
        if "auto_tag_keywords_original" not in existing_columns:
            await conn.execute(text("ALTER TABLE content ADD COLUMN auto_tag_keywords_original TEXT"))
    else:
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS auto_tag_status VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS auto_tag_category VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS auto_tag_keywords_en TEXT"))
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS auto_tag_keywords_original TEXT"))


async def _ensure_content_reflection_columns(conn) -> None:
    """Backfill reflection_questions column added for question caching."""
    if DATABASE_URL.startswith("sqlite"):
        result = await conn.execute(text("PRAGMA table_info(content)"))
        if "reflection_questions" not in {row[1] for row in result.fetchall()}:
            await conn.execute(text("ALTER TABLE content ADD COLUMN reflection_questions TEXT"))
    else:
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS reflection_questions TEXT"))


async def _ensure_content_memo_column(conn) -> None:
    """Backfill memo column added for user memo feature."""
    if DATABASE_URL.startswith("sqlite"):
        result = await conn.execute(text("PRAGMA table_info(content)"))
        if "memo" not in {row[1] for row in result.fetchall()}:
            await conn.execute(text("ALTER TABLE content ADD COLUMN memo TEXT"))
    else:
        await conn.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS memo TEXT"))
