"""Share data processors for different content types."""

import logging
import re
from abc import ABC, abstractmethod

from src.ai.metadata_extractor import ContentMetadata, MetadataExtractor
from src.constants import ContentType

from .exceptions import (
    DeepLinkValidationError,
    ImageProcessingError,
)
from .share_types import ShareData, ShareDataType
from .utils import (
    URL_EXTRACTION_PATTERN,
    extract_scheme,
    is_http_url,
    validate_non_empty,
)


class BaseShareProcessor(ABC):
    """Abstract base class for share data processors."""

    @property
    @abstractmethod
    def supported_types(self) -> list[ShareDataType]:
        """Return list of share data types this processor handles."""
        pass

    @abstractmethod
    async def process(self, share_data: ShareData) -> ContentMetadata:
        """Process share data and return metadata."""
        pass


class URLShareProcessor(BaseShareProcessor):
    """Process URL share data using ContentExtractor and MetadataExtractor."""

    def __init__(
        self,
        content_extractor,
        metadata_extractor: MetadataExtractor,
        summarizer=None,
    ):
        self._content_extractor = content_extractor
        self._metadata_extractor = metadata_extractor
        self._summarizer = summarizer  # type: ignore[assignment]

    @property
    def supported_types(self) -> list[ShareDataType]:
        return [ShareDataType.URL]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        url = validate_non_empty(share_data.content, "URL content is empty.")
        metadata_hints = share_data.metadata or {}
        options = share_data.options or {}
        auto_summarize = options.get("auto_summarize", True)

        raw_html: str | None = None
        text_content: str | None = None
        try:
            raw_html, text_content = await self._content_extractor.fetch_html_and_text(url)
        except Exception as e:
            logging.warning(f"Failed to extract content from {url}: {e}")

        # Pass raw HTML so MetadataExtractor can parse og:title, <title>, etc.
        metadata = await self._metadata_extractor.extract_metadata(url, html_content=raw_html)
        metadata = self._apply_extension_hints(metadata, metadata_hints, share_data.source_platform)

        if self._summarizer and text_content and auto_summarize:
            try:
                metadata.summary = await self._summarizer.summarize(text_content)
            except Exception as e:
                logging.warning(f"Failed to generate summary for {url}: {e}")

        return metadata

    def _apply_extension_hints(
        self,
        metadata: ContentMetadata,
        hints: dict,
        source_platform: str | None,
    ) -> ContentMetadata:
        hinted_title = hints.get("title")
        hinted_author = hints.get("author")
        hinted_content_type = _parse_content_type(hints.get("content_type"))

        if hinted_title and isinstance(hinted_title, str):
            metadata.title = hinted_title.strip() or metadata.title
        if hinted_author and isinstance(hinted_author, str):
            metadata.author = hinted_author.strip() or metadata.author
        if hinted_content_type:
            metadata.content_type = hinted_content_type
        if source_platform and source_platform.lower() not in {"", "web"}:
            metadata.platform = source_platform.capitalize()

        return metadata


class PlainTextProcessor(BaseShareProcessor):
    """Process plain text share data."""

    @property
    def supported_types(self) -> list[ShareDataType]:
        return [ShareDataType.PLAIN_TEXT]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        text = validate_non_empty(share_data.content, "Plain text content is empty.")
        hints = share_data.metadata or {}
        hinted_url = hints.get("url")
        hinted_title = hints.get("title")
        hinted_author = hints.get("author")
        hinted_content_type = _parse_content_type(hints.get("content_type")) or ContentType.ARTICLE

        # Check if text contains a URL
        url_match = URL_EXTRACTION_PATTERN.search(text)
        if url_match:
            return ContentMetadata(
                platform="Web",
                content_type=hinted_content_type,
                url=url_match.group(),
                title=hinted_title if isinstance(hinted_title, str) else None,
                author=hinted_author if isinstance(hinted_author, str) else None,
            )

        if isinstance(hinted_url, str) and hinted_url.strip() and is_http_url(hinted_url.strip()):
            return ContentMetadata(
                platform=share_data.source_platform or "web",
                content_type=hinted_content_type,
                url=hinted_url.strip(),
                title=hinted_title if isinstance(hinted_title, str) else None,
                author=hinted_author if isinstance(hinted_author, str) else None,
            )

        title = text[:100] if len(text) > 100 else text
        return ContentMetadata(
            platform="clipboard",
            content_type=hinted_content_type,
            url="",
            title=(hinted_title if isinstance(hinted_title, str) and hinted_title.strip() else title),
            author=hinted_author if isinstance(hinted_author, str) else None,
        )


class DeepLinkProcessor(BaseShareProcessor):
    """Process deep link share data."""

    # Pre-compiled deep link patterns for common apps
    DEEP_LINK_PATTERNS = {
        "whatsapp": re.compile(r"whatsapp://send\?(?:text=|phone=)", re.IGNORECASE),
        "telegram": re.compile(r"tg://(?:msg|resolve|call)", re.IGNORECASE),
        "twitter": re.compile(r"twitter://(?:post|user|intent/tweet)", re.IGNORECASE),
        "mailto": re.compile(r"mailto:[^ ]+", re.IGNORECASE),
        "tel": re.compile(r"tel:[^ ]+", re.IGNORECASE),
        "youtube": re.compile(r"youtube://(?:watch|live)", re.IGNORECASE),
        "instagram": re.compile(r"instagram://(?:p|reel)", re.IGNORECASE),
        "facebook": re.compile(r"fb://(?:post|video)", re.IGNORECASE),
    }

    # Content type detection patterns
    VIDEO_INDICATORS = {"video", "watch", "reel", "live"}
    IMAGE_INDICATORS = {"photo", "image", "p/"}
    SOCIAL_APPS = {"whatsapp", "telegram", "twitter", "facebook", "instagram"}

    @property
    def supported_types(self) -> list[ShareDataType]:
        return [ShareDataType.DEEP_LINK]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        deep_link = validate_non_empty(share_data.content, "Deep link content is empty.")

        if "://" not in deep_link and ":" not in deep_link:
            raise DeepLinkValidationError(f"Invalid deep link format: {deep_link}")

        source = self._identify_source(deep_link)
        content_type = self._identify_content_type(source, deep_link)

        return ContentMetadata(
            platform=source.capitalize(),
            content_type=content_type,
            url=deep_link,
        )

    def _identify_source(self, deep_link: str) -> str:
        """Identify the source app/service from deep link."""
        for source, pattern in self.DEEP_LINK_PATTERNS.items():
            if pattern.match(deep_link):
                return source
        return extract_scheme(deep_link)

    def _identify_content_type(self, source: str, deep_link: str) -> ContentType:
        """Identify content type based on source and deep link."""
        deep_link_lower = deep_link.lower()

        if any(indicator in deep_link_lower for indicator in self.VIDEO_INDICATORS):
            return ContentType.VIDEO

        if any(indicator in deep_link_lower for indicator in self.IMAGE_INDICATORS):
            return ContentType.IMAGE

        if source in self.SOCIAL_APPS:
            return ContentType.SOCIAL_POST

        if source in ("mailto", "tel"):
            return ContentType.ARTICLE

        return ContentType.DEEP_LINK


class ImageProcessor(BaseShareProcessor):
    """Process image share data."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    @property
    def supported_types(self) -> list[ShareDataType]:
        return [ShareDataType.IMAGE]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        image_data = validate_non_empty(share_data.content, "Image content is empty.")

        if not self._is_valid_image_data(image_data):
            raise ImageProcessingError("Invalid image data format.")

        return ContentMetadata(
            platform=share_data.source_platform or "unknown",
            content_type=ContentType.IMAGE,
            url=image_data if is_http_url(image_data) else "",
        )

    def _is_valid_image_data(self, data: str) -> bool:
        """Check if data is valid image format (base64, URL, or file path)."""
        if data.startswith("data:image/"):
            return True
        if is_http_url(data):
            return True
        return any(data.endswith(ext) for ext in self.IMAGE_EXTENSIONS)


def _parse_content_type(value: object) -> ContentType | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    alias_map = {
        "social": ContentType.SOCIAL_POST,
        "text": ContentType.ARTICLE,
        "unknown": ContentType.ARTICLE,
    }
    mapped = alias_map.get(normalized)
    if mapped:
        return mapped

    try:
        return ContentType(normalized)
    except ValueError:
        return None
