"""Tests for application-level middleware (GZip, security headers, etc.)."""

import httpx
from fastapi import APIRouter
from fastapi.middleware.gzip import GZipMiddleware
from httpx import ASGITransport

from src.api.app import app


async def test_gzip_encoding_returned_when_client_accepts_gzip(db):
    """GZip middleware should be registered and negotiate via Accept-Encoding."""
    assert any(m.cls is GZipMiddleware for m in app.user_middleware), (
        "GZipMiddleware is not registered in app.py"
    )

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        plain = await client.get("/openapi.json", headers={"Accept-Encoding": "identity"})
        gzip = await client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})

    assert plain.status_code == 200
    assert gzip.status_code == 200
    assert plain.json()["openapi"] == gzip.json()["openapi"]
    assert "Accept-Encoding" in gzip.headers.get("vary", ""), (
        "Expected Vary: Accept-Encoding for gzip-negotiated response"
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
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert resp.headers["X-Download-Options"] == "noopen"
    assert resp.headers["X-Permitted-Cross-Domain-Policies"] == "none"
