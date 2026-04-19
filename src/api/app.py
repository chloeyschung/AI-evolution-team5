"""FastAPI application entry point."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from ..ai.summarizer import Summarizer
from ..data.database import init_db
from ..ingestion.extractor import ContentExtractor
from ..ingestion.share_handler import ShareHandler
from ..config import settings
from ..middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from ..middleware.security_headers import security_headers_middleware
from ..utils.http_client import HttpClientPool
from .routers import auth, content, swipe, user, integrations, ai, account, well_known
from .routers.integrations import _background_tasks


logger = logging.getLogger(__name__)

# DAT-003: background purge task handle
_purge_task: asyncio.Task | None = None

PURGE_INTERVAL_SECONDS = 86_400  # 24 hours
RECOVERY_WINDOW_DAYS = 30


async def _purge_expired_soft_deletes() -> None:
    """DAT-003: Permanently hard-delete rows where is_deleted=True and deleted_at > 30 days ago.

    Runs once per day as a background task. Deletes Content and InterestTag rows only.
    SwipeHistory is never soft-deleted and is excluded.
    """
    from sqlalchemy import delete as sql_delete
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    from ..data.database import engine  # reuse existing engine
    from ..data.models import Content, ContentTag, InterestTag
    from ..utils.datetime_utils import utc_now

    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    while True:
        try:
            await asyncio.sleep(PURGE_INTERVAL_SECONDS)
            cutoff = utc_now() - timedelta(days=RECOVERY_WINDOW_DAYS)

            async with AsyncSessionLocal() as session:
                # Find expired Content IDs for cascade deleting ContentTags
                from sqlalchemy import select
                expired_ids_result = await session.execute(
                    select(Content.id).where(
                        Content.is_deleted == True,  # noqa: E712
                        Content.deleted_at < cutoff,
                    )
                )
                expired_ids = [row[0] for row in expired_ids_result.fetchall()]

                if expired_ids:
                    await session.execute(
                        sql_delete(ContentTag).where(ContentTag.content_id.in_(expired_ids))
                    )
                    await session.execute(
                        sql_delete(Content).where(Content.id.in_(expired_ids))
                    )

                # Purge expired InterestTag rows
                await session.execute(
                    sql_delete(InterestTag).where(
                        InterestTag.is_deleted == True,  # noqa: E712
                        InterestTag.deleted_at < cutoff,
                    )
                )

                await session.commit()
                logger.info("DAT-003 purge: removed %d expired content rows", len(expired_ids))

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("DAT-003 purge task error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global _purge_task

    await init_db()

    # Initialize ShareHandler with dependencies (Task #11: DI pattern)
    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    summarizer: Summarizer | None = None
    if summarizer_api_key:
        summarizer = Summarizer(api_key=summarizer_api_key)

    content_extractor = ContentExtractor()
    app.state.share_handler = ShareHandler(
        content_extractor=content_extractor,
        summarizer=summarizer,
    )

    # DAT-003: Start daily soft-delete purge task
    _purge_task = asyncio.create_task(_purge_expired_soft_deletes())

    yield

    # Shutdown: cancel background tasks and close HTTP client pool
    if _purge_task and not _purge_task.done():
        _purge_task.cancel()
        try:
            await _purge_task
        except asyncio.CancelledError:
            pass

    for task in _background_tasks:
        if not task.done():
            task.cancel()
    if _background_tasks:
        await asyncio.gather(*_background_tasks, return_exceptions=True)
    _background_tasks.clear()

    # Close HTTP client pool
    await HttpClientPool.close()


app = FastAPI(
    title="Briefly API",
    description="Hybrid Storage Engine API",
    version="1.0.0",
    lifespan=lifespan,
    exception_handlers={
        RateLimitExceeded: rate_limit_exceeded_handler,
    },
)

# Initialize rate limiter
app.state.limiter = limiter


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Unified HTTPException handler for iOS Codable compatibility.

    Normalises all HTTPException responses to the APIError shape:
      {"error": str, "message": str, "code": int, "details": dict | None}

    If exc.detail is already a dict with "error"/"message" keys those are
    promoted to the top level; all other dict keys are moved into "details".
    Plain-string details are mapped to both "error" and "message".
    """
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail.get("error", "error")
        message = detail.get("message", str(detail))
        extra = {k: v for k, v in detail.items() if k not in ("error", "message")}
    else:
        error = str(detail)
        message = str(detail)
        extra = None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error,
            "message": message,
            "code": exc.status_code,
            "details": extra if extra else None,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled runtime exceptions.

    Returns a structured JSON error shape so that iOS Codable types never
    encounter an inconsistent response body on a 500 status code.
    """
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred.", "code": 500},
    )

# CORS middleware — must be added before other middleware so it runs outermost.
# chrome-extension://* cannot be expressed as a glob in allow_origins when
# allow_credentials=True; we use allow_origin_regex instead (matches any
# 32-char extension ID, which is the canonical Chrome extension ID format).
_cors_kwargs: dict = dict(
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.ALLOWED_ORIGIN_REGEX:
    _cors_kwargs["allow_origin_regex"] = settings.ALLOWED_ORIGIN_REGEX
app.add_middleware(CORSMiddleware, **_cors_kwargs)

# Add security headers middleware (SEC-001 compliance)
app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers_middleware)

# GZip compression for JSON responses (iOS API compliance — responses ≥ 1 KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# SlowAPI middleware must be installed for per-route limiter decorators to enforce limits.
app.add_middleware(SlowAPIMiddleware)

app.include_router(well_known.router,   prefix="",        tags=[])
app.include_router(auth.router,         prefix="/api/v1", tags=["auth"])
app.include_router(account.router,      prefix="/api/v1", tags=["account"])
app.include_router(swipe.router,        prefix="/api/v1", tags=["swipe"])
app.include_router(content.router,      prefix="/api/v1", tags=["content"])
app.include_router(user.router,         prefix="/api/v1", tags=["user"])
app.include_router(integrations.router, prefix="/api/v1", tags=["integrations"])
app.include_router(ai.router,           prefix="/api/v1", tags=["ai"])


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "service": "briefly-api"}
