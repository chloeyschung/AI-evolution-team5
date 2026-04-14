"""Share data processors for different content types."""

import re
from abc import ABC, abstractmethod
from typing import List

from src.ai.metadata_extractor import ContentMetadata, ContentType
from src.ai.metadata_extractor import MetadataExtractor
from .share_types import ShareDataType, ShareData
from .exceptions import (
    InvalidShareDataError,
    DeepLinkValidationError,
    ImageProcessingError,
)
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
    def supported_types(self) -> List[ShareDataType]:
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
        summarizer = None,
    ):
        self._content_extractor = content_extractor
        self._metadata_extractor = metadata_extractor
        self._summarizer = summarizer  # type: ignore[assignment]

    @property
    def supported_types(self) -> List[ShareDataType]:
        return [ShareDataType.URL]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        url = validate_non_empty(share_data.content, "URL content is empty.")

        # Extract text content
        try:
            text_content = await self._content_extractor.extract_text(url)
        except Exception:
            text_content = None

        # Extract metadata with HTML content for richer metadata
        metadata = await self._metadata_extractor.extract_metadata(url, html_content=text_content)

        # Generate summary if summarizer is available and text was extracted
        summary = None
        if self._summarizer and text_content:
            try:
                summary = await self._summarizer.summarize(text_content)
            except Exception:
                pass  # Summary generation failed, continue without summary

        # Update metadata with summary
        metadata.summary = summary

        return metadata


class PlainTextProcessor(BaseShareProcessor):
    """Process plain text share data."""

    @property
    def supported_types(self) -> List[ShareDataType]:
        return [ShareDataType.PLAIN_TEXT]

    async def process(self, share_data: ShareData) -> ContentMetadata:
        text = validate_non_empty(share_data.content, "Plain text content is empty.")

        # Check if text contains a URL
        url_match = URL_EXTRACTION_PATTERN.search(text)
        if url_match:
            return ContentMetadata(
                platform="Web",
                content_type=ContentType.ARTICLE,
                url=url_match.group(),
            )

        title = text[:100] if len(text) > 100 else text
        return ContentMetadata(
            platform="clipboard",
            content_type=ContentType.ARTICLE,
            url="",
            title=title,
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
    def supported_types(self) -> List[ShareDataType]:
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
    def supported_types(self) -> List[ShareDataType]:
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
