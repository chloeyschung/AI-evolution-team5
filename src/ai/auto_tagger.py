"""Gemini 2.5 Flash auto-tagger for Briefly content.

Generates a fixed category and bilingual keyword list from title + summary.
Rate-limited to respect Gemini free tier (~10 RPM, 250 RPD).
Never raises — failures return None so content save is never blocked.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from urllib.parse import urlencode

from src.constants import AUTO_TAG_CATEGORIES
from src.utils.http_client import async_client_context

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
GEMINI_TIMEOUT = 30.0
GEMINI_RETRY_DELAY = 6.0  # safe gap for 10 RPM free tier

# Max 3 concurrent Gemini calls to stay within free-tier RPM
_semaphore = asyncio.Semaphore(3)

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "category": {
            "type": "STRING",
            "enum": AUTO_TAG_CATEGORIES,
        },
        "keywords_en": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "keywords_original": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": ["category", "keywords_en", "keywords_original"],
}


@dataclass
class AutoTagResult:
    category: str
    keywords_en: list[str]
    keywords_original: list[str]


def _build_prompt(title: str, summary: str | None) -> str:
    lines = [f"Title: {title}"]
    if summary:
        lines.append(f"Summary:\n{summary}")
    lines.append(
        "\nClassify this content:\n"
        f"1. category — pick exactly one: {AUTO_TAG_CATEGORIES}\n"
        "2. keywords_en — 2 to 3 English noun phrases (key topics)\n"
        "3. keywords_original — same concepts in the original language of the content\n"
        "   (if the content is already in English, keywords_original == keywords_en)\n"
        "Return JSON only."
    )
    return "\n".join(lines)


def _build_url(api_key: str) -> str:
    endpoint = f"{GEMINI_BASE_URL}/v1beta/models/{GEMINI_MODEL}:generateContent"
    return f"{endpoint}?{urlencode({'key': api_key})}"


def _build_payload(prompt: str) -> dict:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _RESPONSE_SCHEMA,
            "maxOutputTokens": 512,
            "temperature": 0.1,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }


def _parse_response(data: dict) -> AutoTagResult:
    import re
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # gemini-2.5-flash sometimes wraps JSON in natural language — extract the object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group())

    category = parsed.get("category", "Other")
    if category not in AUTO_TAG_CATEGORIES:
        category = "Other"

    def _clean_keywords(raw: list) -> list[str]:
        cleaned = [str(k).strip()[:50] for k in raw if k and str(k).strip()]
        # Ensure at least 2, at most 3
        while len(cleaned) < 2:
            cleaned.append("")
        return cleaned[:3]

    return AutoTagResult(
        category=category,
        keywords_en=_clean_keywords(parsed.get("keywords_en", [])),
        keywords_original=_clean_keywords(parsed.get("keywords_original", [])),
    )


async def tag(title: str, summary: str | None, api_key: str) -> AutoTagResult | None:
    """Call Gemini to generate category + keywords for a piece of content.

    Returns AutoTagResult on success, None after 1 retry failure.
    Never raises — all exceptions are caught and logged.
    """
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured; skipping auto-tag")
        return None

    if not title and not summary:
        return None

    prompt = _build_prompt(title or "", summary)
    url = _build_url(api_key)
    payload = _build_payload(prompt)

    async with _semaphore:
        for attempt in range(2):  # initial attempt + 1 retry
            try:
                async with async_client_context() as client:
                    response = await client.post(url, json=payload, timeout=GEMINI_TIMEOUT)

                if response.status_code == 429:
                    logger.warning("Gemini rate limit (attempt %d/2)", attempt + 1)
                    if attempt == 0:
                        await asyncio.sleep(GEMINI_RETRY_DELAY)
                        continue
                    return None

                if response.status_code != 200:
                    logger.warning(
                        "Gemini HTTP %d (attempt %d/2): %s",
                        response.status_code, attempt + 1, response.text[:300],
                    )
                    if attempt == 0:
                        await asyncio.sleep(GEMINI_RETRY_DELAY)
                        continue
                    return None

                logger.debug("Gemini raw response: %s", response.text[:500])
                return _parse_response(response.json())

            except Exception as exc:
                raw = getattr(response, "text", "")[:300] if "response" in dir() else ""
                logger.warning("Gemini tag attempt %d/2 error: %s | body: %s", attempt + 1, exc, raw)
                if attempt == 0:
                    await asyncio.sleep(GEMINI_RETRY_DELAY)

    return None
