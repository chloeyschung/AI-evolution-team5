"""Tests for GET /api/v1/config/app (iOS lifecycle config endpoint)."""

import pytest


async def test_app_config_returns_200(async_client, db):
    resp = await async_client.get("/api/v1/config/app")
    assert resp.status_code == 200


async def test_app_config_has_required_fields(async_client, db):
    resp = await async_client.get("/api/v1/config/app")
    data = resp.json()
    assert "min_version" in data
    assert "min_ios_version" in data
    assert "is_maintenance" in data
    assert isinstance(data["is_maintenance"], bool)


async def test_app_config_min_version_is_string(async_client, db):
    resp = await async_client.get("/api/v1/config/app")
    data = resp.json()
    assert isinstance(data["min_version"], str)
    assert len(data["min_version"]) > 0


async def test_app_config_not_in_maintenance_by_default(async_client, db):
    resp = await async_client.get("/api/v1/config/app")
    data = resp.json()
    assert data["is_maintenance"] is False
