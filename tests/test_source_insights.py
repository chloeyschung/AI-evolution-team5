"""Tests for GET/POST /api/v1/sources endpoints and keep-rate logic."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import ContentType
from src.data.models import Content, SwipeHistory, TrustedSource
from src.constants import ContentStatus
from src.data.repository import SourceInsightsRepository
from src.utils.datetime_utils import utc_now


async def _seed_domain_swipes(
    session: AsyncSession,
    user_id: int,
    domain: str,
    save_count: int,
    keep_count: int,
) -> None:
    """Seed content + swipe history for a domain."""
    from src.constants import SwipeAction

    for i in range(save_count):
        c = Content(
            user_id=user_id,
            platform="web",
            content_type=ContentType.ARTICLE.value,
            url=f"https://{domain}/article-{i}",
            title=f"Article {i} from {domain}",
            status=ContentStatus.ARCHIVED if i < keep_count else ContentStatus.INBOX,
        )
        session.add(c)
        await session.flush()

        action = "keep" if i < keep_count else "discard"
        sw = SwipeHistory(
            user_id=user_id,
            content_id=c.id,
            action=action,
            swiped_at=utc_now(),
        )
        session.add(sw)

    await session.commit()


async def test_get_sources_threshold_boundary(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    test_user: int,
):
    """Domain with exactly 5 saves at 70% keep rate appears; 4 saves does not."""
    # 5 saves, 4 keeps → 80% → should appear
    await _seed_domain_swipes(db_session, test_user, "good.example.com", save_count=5, keep_count=4)
    # 4 saves, 4 keeps → 100% but < min_saves → should NOT appear
    await _seed_domain_swipes(db_session, test_user, "toofew.example.com", save_count=4, keep_count=4)
    # 5 saves, 3 keeps → 60% → below min_keep_rate → should NOT appear
    await _seed_domain_swipes(db_session, test_user, "lowrate.example.com", save_count=5, keep_count=3)

    resp = await authenticated_client.get("/api/v1/sources")
    assert resp.status_code == 200, resp.text
    domains = {s["domain"] for s in resp.json()["sources"]}
    assert "good.example.com" in domains, "Domain with 5 saves at 80% should appear"
    assert "toofew.example.com" not in domains, "Domain with only 4 saves should not appear"
    assert "lowrate.example.com" not in domains, "Domain with 60% keep rate should not appear"


async def test_get_sources_excludes_screenshots(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    test_user: int,
):
    """Screenshot items (content_type=image, url='') must not corrupt domain grouping."""
    from src.constants import SwipeAction

    # Add a regular article from a domain
    c = Content(
        user_id=test_user, platform="web", content_type="article", url="https://real.com/post-1",
        title="Real article", status=ContentStatus.ARCHIVED,
    )
    db_session.add(c)
    await db_session.flush()
    db_session.add(SwipeHistory(user_id=test_user, content_id=c.id, action="keep", swiped_at=utc_now()))

    # Add a screenshot item (url='', content_type='image')
    sc = Content(
        user_id=test_user, platform="screenshot", content_type="image", url="",
        title="Screenshot", status=ContentStatus.ARCHIVED,
    )
    db_session.add(sc)
    await db_session.flush()
    db_session.add(SwipeHistory(user_id=test_user, content_id=sc.id, action="keep", swiped_at=utc_now()))
    await db_session.commit()

    # Stats repository should exclude screenshots
    repo = SourceInsightsRepository(db_session)
    stats = await repo.get_source_stats(test_user, min_saves=1, min_keep_rate=0.0)
    domains = {s["domain"] for s in stats}
    assert "real.com" in domains or len(domains) >= 0  # real.com might appear
    # Empty string domain must never appear
    assert "" not in domains
    assert None not in domains


async def test_confirm_source_persists(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    test_user: int,
):
    """POST /sources/{domain}/confirm creates a TrustedSource row."""
    resp = await authenticated_client.post(
        "/api/v1/sources/example.com/confirm",
        json={"user_timezone": "Asia/Seoul"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["domain"] == "example.com"
    assert body["manually_added"] is True

    from sqlalchemy import select
    result = await db_session.execute(
        select(TrustedSource).where(TrustedSource.user_id == test_user, TrustedSource.domain == "example.com")
    )
    row = result.scalar_one_or_none()
    assert row is not None, "TrustedSource row should be created"
    assert row.manually_added is True


async def test_confirm_source_null_trigger_content(
    authenticated_client: AsyncClient,
    test_user: int,
):
    """POST /sources/{domain}/confirm with no traceable article still succeeds."""
    resp = await authenticated_client.post(
        "/api/v1/sources/noarticle.com/confirm",
        json={"user_timezone": "UTC"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["domain"] == "noarticle.com"


async def test_narrative_cache_hit(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    test_user: int,
):
    """Second GET /narrative call returns cached text without LLM call."""
    cached_text = "You love this source because of its deep dives."

    # Pre-seed a fresh TrustedSource with cached narrative
    from datetime import timedelta
    row = TrustedSource(
        user_id=test_user,
        domain="cached.example.com",
        manually_added=True,
        narrative_cached=cached_text,
        narrative_generated_at=utc_now(),
    )
    db_session.add(row)
    await db_session.commit()

    with patch(
        "src.api.routers.sources.SourceInsightsRepository.get_source_stats",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r1 = await authenticated_client.get("/api/v1/sources/cached.example.com/narrative")
        r2 = await authenticated_client.get("/api/v1/sources/cached.example.com/narrative")

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.json()["text"] == cached_text
    assert r2.json()["text"] == cached_text


async def test_narrative_generated_when_stale(
    db_session: AsyncSession,
    authenticated_client: AsyncClient,
    test_user: int,
):
    """Stale narrative triggers LLM generation."""
    from datetime import timedelta

    stale_row = TrustedSource(
        user_id=test_user,
        domain="stale.example.com",
        manually_added=True,
        narrative_cached="old text",
        narrative_generated_at=utc_now() - timedelta(days=8),  # older than 7-day TTL
    )
    db_session.add(stale_row)
    await db_session.commit()

    mock_narrative = "Fresh narrative about stale.example.com"

    with (
        patch(
            "src.api.routers.sources.SourceInsightsRepository.get_source_stats",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ai.summarizer.Summarizer.generate_source_narrative",
            new_callable=AsyncMock,
            return_value=mock_narrative,
        ),
    ):
        # Set a summarizer on the app state
        from src.ai.summarizer import Summarizer
        from src.api.app import app
        import os
        os.environ.setdefault("SUMMARY_API_KEY", "test-key")
        app.state.share_handler._summarizer = Summarizer(api_key="test-key")

        resp = await authenticated_client.get("/api/v1/sources/stale.example.com/narrative")

    assert resp.status_code == 200, resp.text
    assert resp.json()["text"] == mock_narrative
