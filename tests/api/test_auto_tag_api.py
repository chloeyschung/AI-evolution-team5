"""Integration tests for auto-tag API surface.

Covers:
- GET /content returns auto_tag_* fields in each item
- GET /content?category= filters correctly
- GET /content?category=<invalid> returns 400
- _background_summarize writes auto-tag result to DB
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import AUTO_TAG_CATEGORIES, ContentType
from src.data.models import Content, ContentStatus
from src.utils.datetime_utils import utc_now


# ── helpers ───────────────────────────────────────────────────────────────────


async def _make_content(
    db_session: AsyncSession,
    user_id: int,
    url: str,
    auto_tag_status: str | None = None,
    auto_tag_category: str | None = None,
    keywords_en: list[str] | None = None,
    keywords_original: list[str] | None = None,
) -> Content:
    c = Content(
        user_id=user_id,
        platform="web",
        content_type=ContentType.ARTICLE,
        url=url,
        title="Test Article",
        status=ContentStatus.INBOX,
        is_deleted=False,
        created_at=utc_now(),
        updated_at=utc_now(),
        auto_tag_status=auto_tag_status,
        auto_tag_category=auto_tag_category,
        auto_tag_keywords_en=json.dumps(keywords_en) if keywords_en is not None else None,
        auto_tag_keywords_original=json.dumps(keywords_original) if keywords_original is not None else None,
    )
    db_session.add(c)
    await db_session.commit()
    return c


# ── ContentResponse fields ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_content_includes_auto_tag_fields_when_tagged(
    authenticated_client, db_session, test_user
):
    await _make_content(
        db_session, test_user,
        url="https://example.com/tagged",
        auto_tag_status="tagged",
        auto_tag_category="Tech",
        keywords_en=["AI", "LLM"],
        keywords_original=["인공지능", "LLM"],
    )
    r = await authenticated_client.get("/api/v1/content")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["auto_tag_status"] == "tagged"
    assert item["auto_tag_category"] == "Tech"
    assert item["auto_tag_keywords_en"] == ["AI", "LLM"]
    assert item["auto_tag_keywords_original"] == ["인공지능", "LLM"]


@pytest.mark.asyncio
async def test_list_content_auto_tag_fields_default_when_untagged(
    authenticated_client, db_session, test_user
):
    await _make_content(db_session, test_user, url="https://example.com/untagged")
    r = await authenticated_client.get("/api/v1/content")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["auto_tag_status"] is None
    assert item["auto_tag_category"] is None
    assert item["auto_tag_keywords_en"] == []
    assert item["auto_tag_keywords_original"] == []


# ── category filter ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_category_filter_returns_only_matching_items(
    authenticated_client, db_session, test_user
):
    await _make_content(db_session, test_user, url="https://a.com/1", auto_tag_category="Tech")
    await _make_content(db_session, test_user, url="https://a.com/2", auto_tag_category="Business")
    await _make_content(db_session, test_user, url="https://a.com/3", auto_tag_category="Tech")

    r = await authenticated_client.get("/api/v1/content?category=Tech")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["auto_tag_category"] == "Tech"


@pytest.mark.asyncio
async def test_category_filter_excludes_untagged_items(
    authenticated_client, db_session, test_user
):
    await _make_content(db_session, test_user, url="https://b.com/1", auto_tag_category="Business")
    await _make_content(db_session, test_user, url="https://b.com/2")  # no category

    r = await authenticated_client.get("/api/v1/content?category=Tech")
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_no_category_filter_returns_all_items(
    authenticated_client, db_session, test_user
):
    await _make_content(db_session, test_user, url="https://c.com/1", auto_tag_category="Tech")
    await _make_content(db_session, test_user, url="https://c.com/2", auto_tag_category="News")
    await _make_content(db_session, test_user, url="https://c.com/3")

    r = await authenticated_client.get("/api/v1/content")
    assert r.status_code == 200
    assert r.json()["total"] == 3


@pytest.mark.asyncio
async def test_all_valid_categories_accepted(authenticated_client, db_session, test_user):
    for cat in AUTO_TAG_CATEGORIES:
        r = await authenticated_client.get(f"/api/v1/content?category={cat}")
        assert r.status_code == 200, f"Expected 200 for category={cat}, got {r.status_code}"


@pytest.mark.asyncio
async def test_invalid_category_returns_400(authenticated_client, db_session, test_user):
    r = await authenticated_client.get("/api/v1/content?category=InvalidCategory")
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_category"


@pytest.mark.asyncio
async def test_category_filter_combined_with_status_filter(
    authenticated_client, db_session, test_user
):
    await _make_content(
        db_session, test_user,
        url="https://d.com/1",
        auto_tag_category="Tech",
    )
    archived = await _make_content(
        db_session, test_user,
        url="https://d.com/2",
        auto_tag_category="Tech",
    )
    # Manually set archived status
    archived.status = ContentStatus.ARCHIVED
    await db_session.commit()

    r = await authenticated_client.get("/api/v1/content?category=Tech&status=inbox")
    assert r.status_code == 200
    assert r.json()["total"] == 1


# ── _background_summarize integration ────────────────────────────────────────


@pytest.mark.asyncio
async def test_background_summarize_writes_tagged_status(db_session, test_user):
    """After summarization, auto_tag_status becomes 'tagged' when Gemini succeeds."""
    from tests.conftest import AsyncTestingSessionLocal

    from src.api.routers.content import _background_summarize
    from src.data.repository import ContentRepository

    content = await _make_content(db_session, test_user, url="https://e.com/bg-test")
    content_id = content.id

    mock_summarizer = MagicMock()
    mock_summarizer.summarize = AsyncMock(return_value="• Point 1\n• Point 2\n• Point 3")
    mock_summarizer.generate_title = AsyncMock(return_value="Generated Title")

    mock_extractor = MagicMock()
    mock_extractor.fetch_html_and_text = AsyncMock(return_value=("<html/>", "Full article text here"))

    mock_gemini_response = MagicMock()
    mock_gemini_response.status_code = 200
    mock_gemini_response.json = MagicMock(return_value={
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "category": "Tech",
            "keywords_en": ["AI", "NLP"],
            "keywords_original": ["인공지능", "자연어처리"],
        })}]}}]
    })

    # Patch AsyncSessionLocal used inside _background_summarize to use the test DB
    with patch("src.api.routers.content.AsyncSessionLocal", AsyncTestingSessionLocal), \
         patch("src.api.routers.content.settings") as mock_settings, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_settings.GEMINI_API_KEY = "test-gemini-key"
        mock_post.return_value = mock_gemini_response

        await _background_summarize(
            content_id=content_id,
            user_id=test_user,
            url="https://e.com/bg-test",
            content_extractor=mock_extractor,
            summarizer=mock_summarizer,
        )

    async with AsyncTestingSessionLocal() as verify_session:
        repo = ContentRepository(verify_session)
        updated = await repo.get_by_id(content_id)
        assert updated.auto_tag_status == "tagged"
        assert updated.auto_tag_category == "Tech"
        kw = json.loads(updated.auto_tag_keywords_en)
        assert "AI" in kw


@pytest.mark.asyncio
async def test_background_summarize_writes_failed_status_when_gemini_fails(
    db_session, test_user
):
    """auto_tag_status becomes 'failed' when Gemini returns an error."""
    from tests.conftest import AsyncTestingSessionLocal

    from src.api.routers.content import _background_summarize
    from src.data.repository import ContentRepository

    content = await _make_content(db_session, test_user, url="https://f.com/fail-test")
    content_id = content.id

    mock_summarizer = MagicMock()
    mock_summarizer.summarize = AsyncMock(return_value="• Line 1\n• Line 2\n• Line 3")
    mock_summarizer.generate_title = AsyncMock(return_value="Title")

    mock_extractor = MagicMock()
    mock_extractor.fetch_html_and_text = AsyncMock(return_value=("<html/>", "Article text"))

    mock_gemini_500 = MagicMock()
    mock_gemini_500.status_code = 500

    with patch("src.api.routers.content.AsyncSessionLocal", AsyncTestingSessionLocal), \
         patch("src.api.routers.content.settings") as mock_settings, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_settings.GEMINI_API_KEY = "test-gemini-key"
        mock_post.return_value = mock_gemini_500

        await _background_summarize(
            content_id=content_id,
            user_id=test_user,
            url="https://f.com/fail-test",
            content_extractor=mock_extractor,
            summarizer=mock_summarizer,
        )

    async with AsyncTestingSessionLocal() as verify_session:
        repo = ContentRepository(verify_session)
        updated = await repo.get_by_id(content_id)
        assert updated.auto_tag_status == "failed"
        assert updated.auto_tag_category is None


@pytest.mark.asyncio
async def test_background_summarize_skips_tagging_when_no_gemini_key(
    db_session, test_user
):
    """No auto-tag DB write when GEMINI_API_KEY is empty."""
    from tests.conftest import AsyncTestingSessionLocal

    from src.api.routers.content import _background_summarize
    from src.data.repository import ContentRepository

    content = await _make_content(db_session, test_user, url="https://g.com/no-key")
    content_id = content.id

    mock_summarizer = MagicMock()
    mock_summarizer.summarize = AsyncMock(return_value="• Line 1\n• Line 2\n• Line 3")
    mock_summarizer.generate_title = AsyncMock(return_value="Title")

    mock_extractor = MagicMock()
    mock_extractor.fetch_html_and_text = AsyncMock(return_value=("<html/>", "Article text"))

    with patch("src.api.routers.content.AsyncSessionLocal", AsyncTestingSessionLocal), \
         patch("src.api.routers.content.settings") as mock_settings, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_settings.GEMINI_API_KEY = ""  # no key

        await _background_summarize(
            content_id=content_id,
            user_id=test_user,
            url="https://g.com/no-key",
            content_extractor=mock_extractor,
            summarizer=mock_summarizer,
        )
        assert mock_post.call_count == 0  # Gemini never called

    async with AsyncTestingSessionLocal() as verify_session:
        repo = ContentRepository(verify_session)
        updated = await repo.get_by_id(content_id)
        assert updated.auto_tag_status is None  # untouched
