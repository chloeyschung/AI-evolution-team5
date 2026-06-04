import re
from urllib.parse import urlparse

import httpx

_LINKEDIN_HOST_RE = re.compile(r"(?:^|\.)linkedin\.com$", re.IGNORECASE)
_OEMBED_URL = "https://www.linkedin.com/oembed?url={url}&format=json"


def is_linkedin_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return bool(_LINKEDIN_HOST_RE.search(host))


async def fetch_linkedin_text(url: str) -> str | None:
    """LinkedIn oEmbed API로 title + author를 취득합니다. 실패 시 None을 반환합니다.

    oEmbed는 공개 게시물/아티클에서만 작동합니다. 비공개 콘텐츠나 로그인이
    필요한 피드 게시물은 None을 반환하며, 이 경우 요약을 건너뜁니다.
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(_OEMBED_URL.format(url=url))
            r.raise_for_status()
            data = r.json()
        title = data.get("title", "")
        author = data.get("author_name", "")
        return f"{title}\n{author}".strip() or None
    except Exception:
        return None
