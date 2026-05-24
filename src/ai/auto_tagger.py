"""OpenAI-compatible auto-tagger for Briefly content.

Uses the same Modal/vLLM endpoint as the summarizer (SUMMARY_API_KEY / SUMMARY_BASE_URL).
Generates a fixed category and bilingual keyword list from title + summary.
Never raises — failures return None so content save is never blocked.
"""

import asyncio
import json
import logging
from dataclasses import dataclass

from src.constants import AUTO_TAG_CATEGORIES
from src.utils.http_client import async_client_context

logger = logging.getLogger(__name__)

_TAG_TIMEOUT = 30.0


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


def _parse_response(data: dict) -> AutoTagResult:
    import re
    text = data["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group())

    category = parsed.get("category", "Other")
    if category not in AUTO_TAG_CATEGORIES:
        category = "Other"

    def _clean_keywords(raw: list) -> list[str]:
        cleaned = [str(k).strip()[:50] for k in raw if k and str(k).strip()]
        while len(cleaned) < 2:
            cleaned.append("")
        return cleaned[:3]

    return AutoTagResult(
        category=category,
        keywords_en=_clean_keywords(parsed.get("keywords_en", [])),
        keywords_original=_clean_keywords(parsed.get("keywords_original", [])),
    )


async def tag(title: str, summary: str | None, settings) -> AutoTagResult | None:
    """Call the OpenAI-compatible endpoint to generate category + keywords.

    Returns AutoTagResult on success, None after 3 attempts.
    Never raises — all exceptions are caught and logged.
    """
    modal_tokens_ok = bool(
        getattr(settings, "MODAL_PROXY_TOKEN_ID", "") and
        getattr(settings, "MODAL_PROXY_TOKEN_SECRET", "")
    )
    if not settings.SUMMARY_API_KEY and not modal_tokens_ok:
        logger.warning("No auto-tag credentials configured (SUMMARY_API_KEY or MODAL tokens); skipping")
        return None

    if not title and not summary:
        return None

    # SUMMARY_BASE_URL already contains the full endpoint path (including /v1/chat/completions)
    url = settings.SUMMARY_BASE_URL
    payload = {
        "model": settings.SUMMARY_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(title or "", summary)}],
        "response_format": {"type": "json_object"},
        "max_tokens": 256,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers: dict = {}
    if modal_tokens_ok:
        headers["Modal-Key"] = settings.MODAL_PROXY_TOKEN_ID
        headers["Modal-Secret"] = settings.MODAL_PROXY_TOKEN_SECRET
    if settings.SUMMARY_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SUMMARY_API_KEY}"

    for attempt in range(3):
        try:
            async with async_client_context() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=_TAG_TIMEOUT)

            if response.status_code == 200:
                logger.debug("Auto-tag raw response: %s", response.text[:500])
                return _parse_response(response.json())

            logger.warning(
                "Auto-tag HTTP %d (attempt %d/3): %s",
                response.status_code, attempt + 1, response.text[:300],
            )

        except Exception as exc:
            logger.warning("Auto-tag attempt %d/3 error: %s", attempt + 1, exc)

        if attempt < 2:
            await asyncio.sleep(2 ** attempt)

    return None
