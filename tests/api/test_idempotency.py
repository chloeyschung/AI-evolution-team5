"""Tests for Idempotency-Key header on POST /share."""

import pytest


async def test_share_with_idempotency_key_returns_same_id(authenticated_client, db):
    """Two POST /share requests with the same Idempotency-Key must return the same content id."""
    key = "test-idempotency-key-001"
    resp1 = await authenticated_client.post(
        "/api/v1/share",
        json={"content": "https://example.com/article-idem"},
        headers={"Idempotency-Key": key},
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    resp2 = await authenticated_client.post(
        "/api/v1/share",
        json={"content": "https://example.com/article-idem"},
        headers={"Idempotency-Key": key},
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    assert id1 == id2, f"Idempotency failed: first id={id1}, second id={id2}"


async def test_share_different_idempotency_keys_create_separate_items(authenticated_client, db):
    """Different keys should not deduplicate each other."""
    resp1 = await authenticated_client.post(
        "/api/v1/share",
        json={"content": "https://example.com/article-a"},
        headers={"Idempotency-Key": "key-A"},
    )
    assert resp1.status_code == 201

    resp2 = await authenticated_client.post(
        "/api/v1/share",
        json={"content": "https://example.com/article-b"},
        headers={"Idempotency-Key": "key-B"},
    )
    assert resp2.status_code == 201

    assert resp1.json()["id"] != resp2.json()["id"]


async def test_share_without_idempotency_key_still_works(authenticated_client, db):
    """POST /share without Idempotency-Key must continue to work normally."""
    resp = await authenticated_client.post(
        "/api/v1/share",
        json={"content": "https://example.com/article-no-key"},
    )
    assert resp.status_code == 201
    assert "id" in resp.json()
