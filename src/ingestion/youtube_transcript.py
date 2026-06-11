"""YouTube transcript and oEmbed fallback extractor (ING-003)."""

import logging
import re

import httpx

YOUTUBE_URL_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)
OEMBED_URL = "https://www.youtube.com/oembed?url={url}&format=json"
PREFERRED_LANGS = ["ko", "en"]
MAX_TRANSCRIPT_CHARS = 6000


def extract_video_id(url: str) -> str | None:
    m = YOUTUBE_URL_RE.search(url)
    return m.group(1) if m else None


async def fetch_youtube_text(url: str) -> str | None:
    """YouTube URL에서 텍스트를 추출한다.

    1단계: youtube-transcript-api로 자막 추출 (한국어 → 영어 → 첫 번째 자막)
    2단계: YouTube oEmbed API로 제목+저자 추출 (fallback)
    실패 시 None 반환 — 호출자가 HTML scraping으로 fallback한다.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    # 1단계: transcript
    try:
        from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        try:
            snippets = api.fetch(video_id, languages=PREFERRED_LANGS)
        except NoTranscriptFound:
            # 선호 언어 자막 없음 — 첫 번째 자막으로 재시도
            tl = api.list(video_id)
            first = next(iter(tl))
            snippets = api.fetch(video_id, languages=[first.language_code])

        text = " ".join(s.text for s in snippets).strip()
        if text:
            logging.info("ING-003: transcript extracted for video %s (%d chars)", video_id, len(text))
            return text[:MAX_TRANSCRIPT_CHARS]
    except TranscriptsDisabled:
        logging.info("ING-003: transcripts disabled for video %s — trying oEmbed", video_id)
    except Exception as exc:  # noqa: BLE001
        logging.warning("ING-003: transcript fetch failed for video %s: %s", video_id, exc)

    # 2단계: oEmbed fallback
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(OEMBED_URL.format(url=url))
            r.raise_for_status()
            data = r.json()
            title = data.get("title", "")
            author = data.get("author_name", "")
            text = f"{title}\n{author}".strip()
            if text:
                logging.info("ING-003: oEmbed fallback used for video %s", video_id)
                return text
    except Exception as exc:  # noqa: BLE001
        logging.warning("ING-003: oEmbed fallback failed for video %s: %s", video_id, exc)

    return None
