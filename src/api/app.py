"""FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from ..ai.summarizer import Summarizer
from ..data.database import init_db
from ..ingestion.extractor import ContentExtractor
from ..ingestion.share_handler import ShareHandler
from ..config import settings
from ..middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from ..middleware.security_headers import security_headers_middleware
from ..utils.http_client import HttpClientPool
from .routes import _background_tasks, router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
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

    yield

    # Shutdown: cancel background tasks and close HTTP client pool
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

app.include_router(router, prefix="/api/v1", tags=["content"])


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "service": "briefly-api"}
