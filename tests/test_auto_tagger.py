"""Unit tests for src/ai/auto_tagger.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.auto_tagger import AutoTagResult, _parse_response, tag
from src.constants import AUTO_TAG_CATEGORIES


# ── helpers ──────────────────────────────────────────────────────────────────


def _gemini_ok(payload: dict) -> dict:
    """Wrap a dict in the Gemini generateContent response envelope."""
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


def _mock_response(status: int, body: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if body is not None:
        r.json = MagicMock(return_value=body)
    return r


# ── _parse_response ───────────────────────────────────────────────────────────


def test_parse_valid_result():
    data = _gemini_ok(
        {
            "category": "Tech",
            "keywords_en": ["machine learning", "fine-tuning"],
            "keywords_original": ["기계학습", "파인튜닝"],
        }
    )
    result = _parse_response(data)
    assert result.category == "Tech"
    assert result.keywords_en == ["machine learning", "fine-tuning"]
    assert result.keywords_original == ["기계학습", "파인튜닝"]


def test_parse_unknown_category_falls_back_to_other():
    data = _gemini_ok(
        {
            "category": "Quantum Physics",  # not in fixed list
            "keywords_en": ["qubit", "entanglement"],
            "keywords_original": ["qubit", "entanglement"],
        }
    )
    result = _parse_response(data)
    assert result.category == "Other"


def test_parse_all_valid_categories_accepted():
    for cat in AUTO_TAG_CATEGORIES:
        data = _gemini_ok(
            {
                "category": cat,
                "keywords_en": ["a", "b"],
                "keywords_original": ["a", "b"],
            }
        )
        assert _parse_response(data).category == cat


def test_parse_too_many_keywords_truncated_to_three():
    data = _gemini_ok(
        {
            "category": "Tech",
            "keywords_en": ["a", "b", "c", "d", "e"],
            "keywords_original": ["x", "y", "z", "w", "v"],
        }
    )
    result = _parse_response(data)
    assert len(result.keywords_en) == 3
    assert len(result.keywords_original) == 3


def test_parse_too_few_keywords_padded_to_two():
    data = _gemini_ok(
        {
            "category": "Essays",
            "keywords_en": ["only one"],
            "keywords_original": [],
        }
    )
    result = _parse_response(data)
    assert len(result.keywords_en) == 2
    assert len(result.keywords_original) == 2


def test_parse_keyword_trimmed_at_50_chars():
    long = "x" * 60
    data = _gemini_ok(
        {
            "category": "Tech",
            "keywords_en": [long, "short"],
            "keywords_original": [long, "short"],
        }
    )
    result = _parse_response(data)
    assert all(len(k) <= 50 for k in result.keywords_en)


# ── tag() — no-op paths ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_returns_none_when_api_key_empty():
    result = await tag("Some title", "Some summary", api_key="")
    assert result is None


@pytest.mark.asyncio
async def test_tag_returns_none_when_both_title_and_summary_empty():
    result = await tag("", None, api_key="test-key")
    assert result is None


# ── tag() — happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_success_returns_autotag_result():
    body = {
        "category": "Business",
        "keywords_en": ["startup", "venture capital"],
        "keywords_original": ["스타트업", "벤처캐피탈"],
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, _gemini_ok(body))
        result = await tag("YC S25 batch", "Thirty startups raised seed rounds.", api_key="key")

    assert isinstance(result, AutoTagResult)
    assert result.category == "Business"
    assert "startup" in result.keywords_en
    assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_tag_url_contains_api_key():
    body = {
        "category": "Tech",
        "keywords_en": ["AI", "GPU"],
        "keywords_original": ["AI", "GPU"],
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, _gemini_ok(body))
        await tag("Title", "Summary", api_key="MY_SECRET_KEY")
        url_used = mock_post.call_args.args[0]

    assert "MY_SECRET_KEY" in url_used
    assert "gemini-2.5-flash" in url_used


@pytest.mark.asyncio
async def test_tag_payload_includes_response_schema():
    body = {
        "category": "Tech",
        "keywords_en": ["AI", "GPU"],
        "keywords_original": ["AI", "GPU"],
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(200, _gemini_ok(body))
        await tag("Title", "Summary", api_key="key")
        sent_payload = mock_post.call_args.kwargs["json"]

    cfg = sent_payload["generationConfig"]
    assert cfg["responseMimeType"] == "application/json"
    assert "responseSchema" in cfg
    assert cfg["responseSchema"]["properties"]["category"]["enum"] == AUTO_TAG_CATEGORIES


# ── tag() — retry behaviour ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_429_retries_once_then_returns_none():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_post.return_value = _mock_response(429)
        result = await tag("Title", "Summary", api_key="key")

    assert result is None
    assert mock_post.call_count == 2  # initial + 1 retry


@pytest.mark.asyncio
async def test_tag_429_then_200_succeeds_on_retry():
    body = {
        "category": "News",
        "keywords_en": ["politics", "election"],
        "keywords_original": ["정치", "선거"],
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_post.side_effect = [
            _mock_response(429),
            _mock_response(200, _gemini_ok(body)),
        ]
        result = await tag("Title", "Summary", api_key="key")

    assert result is not None
    assert result.category == "News"
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_tag_500_retries_once_then_returns_none():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_post.return_value = _mock_response(500)
        result = await tag("Title", "Summary", api_key="key")

    assert result is None
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_tag_network_exception_retries_then_returns_none():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_post.side_effect = Exception("network error")
        result = await tag("Title", "Summary", api_key="key")

    assert result is None
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_tag_never_raises():
    """tag() must absorb all exceptions — content save must never be blocked."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_post.side_effect = RuntimeError("fatal error")
        result = await tag("Title", "Summary", api_key="key")  # must not raise

    assert result is None
