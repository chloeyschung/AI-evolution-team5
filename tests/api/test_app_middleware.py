"""Tests for application-level middleware (GZip, security headers, etc.)."""

import httpx
import pytest
from fastapi import APIRouter
from httpx import ASGITransport

from src.api.app import app


async def test_gzip_encoding_returned_when_client_accepts_gzip(db):
    """GZipMiddleware must compress JSON responses when client sends Accept-Encoding: gzip.

    Uses GET /openapi.json which returns ~85 KB of JSON — well above the
    minimum_size=1000 threshold — and requires no authentication.

    The response must carry Content-Encoding: gzip when the client signals
    Accept-Encoding: gzip.

    This test FAILS until GZipMiddleware is registered in app.py.
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "Accept-Encoding": "gzip",
        },
    ) as client:
        resp = await client.get("/openapi.json")

    assert resp.status_code == 200, f"Expected 200 from /openapi.json, got {resp.status_code}"

    # Primary assertion: GZip middleware must set Content-Encoding: gzip
    assert resp.headers.get("content-encoding") == "gzip", (
        f"Expected 'Content-Encoding: gzip' but got headers: {dict(resp.headers)}\n"
        f"Response body length: {len(resp.content)} bytes\n"
        "GZipMiddleware is not registered in app.py"
    )


async def test_global_exception_handler_returns_structured_json(db):
    """Unhandled RuntimeError must return structured JSON instead of FastAPI default.

    iOS Codable types crash when the error shape is inconsistent. The global
    exception handler must always return:
        {"error": "internal_server_error", "message": "An unexpected error occurred.", "code": 500}

    This test FAILS until the global exception handler is registered in app.py.
    """
    # Register a temporary route that raises an unhandled RuntimeError
    _test_router = APIRouter()

    @_test_router.get("/_test/boom")
    async def _boom():
        raise RuntimeError("boom")

    app.include_router(_test_router)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/_test/boom")

    assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"
    body = resp.json()
    assert body == {
        "error": "internal_server_error",
        "message": "An unexpected error occurred.",
        "code": 500,
    }, (
        f"Expected structured error JSON but got: {body}\n"
        "Global exception handler is not registered in app.py"
    )
