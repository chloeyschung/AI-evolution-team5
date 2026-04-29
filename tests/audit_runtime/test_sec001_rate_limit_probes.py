import pytest


@pytest.mark.asyncio
async def test_rate_limit_enforced_on_login(async_client):
    from src.middleware.rate_limiter import limiter

    # Ensure a clean limiter state for this test run.
    limiter._storage.reset()

    # /auth/login is decorated with @limiter.limit("3/minute") in src/api/routers/auth.py
    # Send 4 requests with a syntactically valid body so the endpoint function runs.
    bodies = []
    for _ in range(4):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "203.0.113.10"},
        )
        bodies.append((resp.status_code, resp.headers, resp.json()))

    # First 3 calls should reach app logic and fail with 401 (invalid credentials).
    assert [s for (s, _, _) in bodies[:3]] == [401] * 3

    # 4th call should be rate-limited.
    status, headers, body = bodies[3]
    assert status == 429
    assert body["error"] == "rate_limit_exceeded"
    assert body["code"] == 429

    # Runtime evidence: in current configuration SlowAPI is not emitting
    # Retry-After or X-RateLimit-* headers on 429 responses.
    assert headers.get("Retry-After") is None
    assert headers.get("X-RateLimit-Limit") is None


@pytest.mark.asyncio
async def test_refresh_rate_limited(async_client):
    """
    Runtime probe: /auth/refresh is protected by @limiter.limit("10/minute").
    After enough invalid refresh attempts from one client IP, endpoint returns 429.
    """
    from src.middleware.rate_limiter import limiter

    limiter._storage.reset()

    statuses = []
    for i in range(15):
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": f"invalid-{i}"},
            headers={"X-Forwarded-For": "203.0.113.10"},
        )
        statuses.append(resp.status_code)

    # First several requests should execute endpoint logic and fail auth.
    assert statuses[:10] == [401] * 10
    # Rate limiter should enforce a 429 once the 10/minute threshold is exceeded.
    assert 429 in statuses


@pytest.mark.asyncio
async def test_no_rate_limit_on_auth_status(async_client):
    # /auth/status is NOT decorated with @limiter.limit in src/api/routers/auth.py.
    # Hammer it and assert we don't get a 429.
    for _ in range(25):
        resp = await async_client.get("/api/v1/auth/status")
        assert resp.status_code != 429
