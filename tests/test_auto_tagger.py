"""Unit tests for src/ai/auto_tagger.py."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.auto_tagger import AutoTagResult, _parse_response, tag
from src.constants import AUTO_TAG_CATEGORIES


# ── helpers ──────────────────────────────────────────────────────────────────


def _openai_ok(payload: dict) -> dict:
    """Wrap a dict in the OpenAI chat/completions response envelope."""
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def _mock_response(status: int, body: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = ""
    if body is not None:
        r.json = MagicMock(return_value=body)
    return r


def _mock_settings(api_key: str = "test-key") -> MagicMock:
    s = MagicMock()
    s.SUMMARY_API_KEY = api_key
    s.SUMMARY_BASE_URL = "https://api.example.com"
    s.SUMMARY_MODEL = "test-model"
    return s


def _make_ctx(return_value=None, side_effect=None):
    """Return (ctx_fn, mock_client) for patching async_client_context."""
    mock_client = AsyncMock()
    if side_effect is not None:
        mock_client.post = AsyncMock(side_effect=side_effect)
    else:
        mock_client.post = AsyncMock(return_value=return_value)

    @asynccontextmanager
    async def ctx():
        yield mock_client

    return ctx, mock_client


# ── _parse_response ───────────────────────────────────────────────────────────


def test_parse_valid_result():
    data = _openai_ok(
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
    data = _openai_ok(
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
        data = _openai_ok(
            {
                "category": cat,
                "keywords_en": ["a", "b"],
                "keywords_original": ["a", "b"],
            }
        )
        assert _parse_response(data).category == cat


def test_parse_too_many_keywords_truncated_to_three():
    data = _openai_ok(
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
    data = _openai_ok(
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
    data = _openai_ok(
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
    result = await tag("Some title", "Some summary", _mock_settings(api_key=""))
    assert result is None


@pytest.mark.asyncio
async def test_tag_returns_none_when_both_title_and_summary_empty():
    result = await tag("", None, _mock_settings())
    assert result is None


# ── tag() — happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_success_returns_autotag_result():
    body = {
        "category": "Business",
        "keywords_en": ["startup", "venture capital"],
        "keywords_original": ["스타트업", "벤처캐피탈"],
    }
    ctx, mock_client = _make_ctx(return_value=_mock_response(200, _openai_ok(body)))
    with patch("src.ai.auto_tagger.async_client_context", ctx):
        result = await tag("YC S25 batch", "Thirty startups raised seed rounds.", _mock_settings())

    assert isinstance(result, AutoTagResult)
    assert result.category == "Business"
    assert "startup" in result.keywords_en
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_tag_payload_uses_openai_response_format():
    body = {
        "category": "Tech",
        "keywords_en": ["AI", "GPU"],
        "keywords_original": ["AI", "GPU"],
    }
    ctx, mock_client = _make_ctx(return_value=_mock_response(200, _openai_ok(body)))
    with patch("src.ai.auto_tagger.async_client_context", ctx):
        await tag("Title", "Summary", _mock_settings())

    sent_payload = mock_client.post.call_args.kwargs["json"]
    assert sent_payload["response_format"] == {"type": "json_object"}
    assert sent_payload["messages"][0]["role"] == "user"


# ── tag() — retry behaviour ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_429_retries_up_to_three_then_returns_none():
    ctx, mock_client = _make_ctx(side_effect=[
        _mock_response(429),
        _mock_response(429),
        _mock_response(429),
    ])
    with patch("src.ai.auto_tagger.async_client_context", ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await tag("Title", "Summary", _mock_settings())

    assert result is None
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_tag_429_then_200_succeeds_on_retry():
    body = {
        "category": "News",
        "keywords_en": ["politics", "election"],
        "keywords_original": ["정치", "선거"],
    }
    ctx, mock_client = _make_ctx(side_effect=[
        _mock_response(429),
        _mock_response(200, _openai_ok(body)),
    ])
    with patch("src.ai.auto_tagger.async_client_context", ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await tag("Title", "Summary", _mock_settings())

    assert result is not None
    assert result.category == "News"
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_tag_500_retries_then_returns_none():
    ctx, mock_client = _make_ctx(return_value=_mock_response(500))
    with patch("src.ai.auto_tagger.async_client_context", ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await tag("Title", "Summary", _mock_settings())

    assert result is None
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_tag_network_exception_retries_then_returns_none():
    ctx, mock_client = _make_ctx(side_effect=Exception("network error"))
    with patch("src.ai.auto_tagger.async_client_context", ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await tag("Title", "Summary", _mock_settings())

    assert result is None
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_tag_never_raises():
    """tag() must absorb all exceptions — content save must never be blocked."""
    ctx, mock_client = _make_ctx(side_effect=RuntimeError("fatal error"))
    with patch("src.ai.auto_tagger.async_client_context", ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await tag("Title", "Summary", _mock_settings())  # must not raise

    assert result is None
