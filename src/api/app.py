"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from ..ai.summarizer import Summarizer
from ..data.database import init_db
from ..ingestion.extractor import ContentExtractor
from ..ingestion.share_handler import ShareHandler
from ..middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from ..utils.http_client import HttpClientPool
from .routes import router, _set_share_handler, get_share_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()

    # Initialize ShareHandler with dependencies
    summarizer_api_key = os.getenv("ANTHROPIC_API_KEY")
    summarizer: Summarizer | None = None
    if summarizer_api_key:
        summarizer = Summarizer(api_key=summarizer_api_key)

    content_extractor = ContentExtractor()
    share_handler = ShareHandler(
        content_extractor=content_extractor,
        summarizer=summarizer,
    )
    _set_share_handler(share_handler)

    yield

    # Shutdown: close HTTP client pool
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

app.include_router(router, prefix="/api/v1", tags=["content"])


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "service": "briefly-api"}
