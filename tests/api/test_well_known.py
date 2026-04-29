"""Tests for /.well-known/ endpoints required by iOS Universal Links."""

import httpx
import pytest
from httpx import ASGITransport

from src.api.app import app


async def test_aasa_returns_200(db):
    """GET /.well-known/apple-app-site-association must return HTTP 200.

    iOS Universal Links require this endpoint to exist at the exact path
    with no .json extension.  This test FAILS until the endpoint is registered
    in app.py (currently returns 404).
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/.well-known/apple-app-site-association")

    assert resp.status_code == 200, (
        f"Expected 200 from /.well-known/apple-app-site-association, got {resp.status_code}. "
        "The AASA endpoint is not yet registered in app.py."
    )


async def test_aasa_content_type_is_json(db):
    """GET /.well-known/apple-app-site-association must return Content-Type: application/json.

    iOS requires application/json, NOT application/octet-stream.
    This test FAILS until the endpoint explicitly sets the correct media type.
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/.well-known/apple-app-site-association")

    content_type = resp.headers.get("content-type", "")
    assert "application/json" in content_type, (
        f"Expected Content-Type to contain 'application/json', got: '{content_type}'. "
        "iOS will reject the AASA file if Content-Type is not application/json."
    )


async def test_aasa_body_has_applinks_key(db):
    """GET /.well-known/apple-app-site-association body must contain 'applinks' key.

    The AASA JSON payload must conform to the Apple App Site Association spec.
    This test FAILS until the endpoint returns a valid AASA payload.
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/.well-known/apple-app-site-association")

    assert resp.status_code == 200
    body = resp.json()
    assert "applinks" in body, (
        f"Response body missing 'applinks' key. Got keys: {list(body.keys())}. "
        "The AASA payload must contain an 'applinks' entry per Apple's spec."
    )
    assert "details" in body["applinks"], (
        f"'applinks' is missing 'details'. Got: {body['applinks']}"
    )
    assert isinstance(body["applinks"].get("apps"), list), (
        f"'applinks.apps' must be a list. Got: {body['applinks'].get('apps')}"
    )
