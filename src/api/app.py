"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..data.database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()
    yield


app = FastAPI(
    title="Briefly API",
    description="Hybrid Storage Engine API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1", tags=["content"])


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "service": "briefly-api"}
