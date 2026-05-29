"""Reflection question generator for Briefly content.

Uses the same Modal/vLLM endpoint as the auto-tagger (SUMMARY_* / MODAL_* settings).
Returns 3 open-ended, critical-thinking questions based on article summary and keywords.
Never raises — failures return an empty list so the API response is always safe.
"""

import asyncio
import json
import logging
import re

from src.utils.http_client import async_client_context

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0        # per-attempt HTTP timeout
_TOTAL_TIMEOUT = 10.0  # absolute cap — matches axios client timeout on the frontend


def _build_prompt(summary: str | None, keywords: list[str]) -> str:
    parts = []
    if summary:
        parts.append(f"Article summary:\n{summary}")
    if keywords:
        parts.append(f"Key topics: {', '.join(keywords)}")
    parts.append(
        "\nGenerate exactly 3 reflection questions for a reader of this article.\n"
        "Requirements:\n"
        "- Questions must NOT be factual recall questions that re-check article content\n"
        "- Questions MUST encourage critical thinking, speculation, or personal application\n"
        "- Each question must connect specifically to the article topic — no generic questions\n"
        "- Good examples: 'What second-order effects might this change trigger?', "
        "'Whose perspective is absent from this account?', "
        "'How could this apply to your own context?'\n"
        "Return ONLY a JSON array of exactly 3 question strings. No explanation, no keys."
    )
    return "\n".join(parts)


def _parse_response(data: dict) -> list[str]:
    text = data["choices"][0]["message"]["content"].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        parsed = json.loads(match.group())

    if not isinstance(parsed, list):
        return []

    questions = [str(q).strip() for q in parsed if q and str(q).strip()]
    return questions[:3]


async def generate_questions(
    summary: str | None,
    keywords: list[str],
    settings,
) -> list[str]:
    """Call the OpenAI-compatible endpoint to generate 3 reflection questions.

    Returns a list of up to 3 question strings on success, empty list on failure.
    Never raises.
    """
    modal_tokens_ok = bool(
        getattr(settings, "MODAL_PROXY_TOKEN_ID", "")
        and getattr(settings, "MODAL_PROXY_TOKEN_SECRET", "")
    )
    if not settings.SUMMARY_API_KEY and not modal_tokens_ok:
        logger.warning("No reflection-question credentials configured; skipping")
        return []

    if not summary and not keywords:
        return []

    url = settings.SUMMARY_BASE_URL
    payload = {
        "model": settings.SUMMARY_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(summary, keywords)}],
        "max_tokens": 512,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers: dict = {}
    if modal_tokens_ok:
        headers["Modal-Key"] = settings.MODAL_PROXY_TOKEN_ID
        headers["Modal-Secret"] = settings.MODAL_PROXY_TOKEN_SECRET
    if settings.SUMMARY_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SUMMARY_API_KEY}"

    async def _attempt() -> list[str]:
        for attempt in range(2):
            try:
                async with async_client_context() as client:
                    response = await client.post(url, json=payload, headers=headers, timeout=_TIMEOUT)

                if response.status_code == 200:
                    questions = _parse_response(response.json())
                    if questions:
                        return questions
                    logger.warning("Reflection: empty or unparseable response on attempt %d/2", attempt + 1)
                else:
                    logger.warning(
                        "Reflection HTTP %d (attempt %d/2): %s",
                        response.status_code, attempt + 1, response.text[:300],
                    )

            except Exception as exc:
                logger.warning("Reflection attempt %d/2 error: %s", attempt + 1, exc)

            if attempt < 1:
                await asyncio.sleep(1)

        return []

    try:
        return await asyncio.wait_for(_attempt(), timeout=_TOTAL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("Reflection: total timeout (%.0fs) exceeded", _TOTAL_TIMEOUT)
        return []
