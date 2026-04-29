"""Share handler for mobile share sheet integration."""

from src.ai.metadata_extractor import ContentMetadata, MetadataExtractor
from src.ingestion.extractor import ContentExtractor

from .exceptions import InvalidShareDataError, UnsupportedShareTypeError
from .share_processor import (
    BaseShareProcessor,
    DeepLinkProcessor,
    ImageProcessor,
    PlainTextProcessor,
    URLShareProcessor,
)
from .share_types import ShareData, ShareDataType
from .utils import (
    DEEP_LINK_PATTERN,
    URL_DETECTION_PATTERN,
    is_http_url,
)


class ShareHandler:
    """Handles mobile share sheet data processing."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    def __init__(
        self,
        content_extractor: ContentExtractor,
        metadata_extractor: MetadataExtractor | None = None,
        summarizer=None,
    ):
        """Initialize ShareHandler with required services."""
        self._content_extractor = content_extractor
        # Create metadata extractor if not provided
        self._metadata_extractor = metadata_extractor or MetadataExtractor()
        self._summarizer = summarizer
        self._processors: dict[ShareDataType, BaseShareProcessor] = {
            ShareDataType.URL: URLShareProcessor(content_extractor, self._metadata_extractor, summarizer),
            ShareDataType.PLAIN_TEXT: PlainTextProcessor(),
            ShareDataType.DEEP_LINK: DeepLinkProcessor(),
            ShareDataType.IMAGE: ImageProcessor(),
        }

    def _identify_share_type(self, raw_data: dict) -> ShareDataType:
        """Identify the share data type from raw input."""
        if not isinstance(raw_data, dict):
            raise InvalidShareDataError("Share data must be a dictionary.")

        content = raw_data.get("content")
        if content is None:
            raise InvalidShareDataError("Share data must contain 'content' field.")

        content = str(content).strip()
        if not content:
            raise InvalidShareDataError("Share content cannot be empty.")

        # Check for explicit type hint
        explicit_type = raw_data.get("type")
        if explicit_type:
            try:
                return ShareDataType(explicit_type)
            except ValueError:
                pass

        # Detect URL
        if URL_DETECTION_PATTERN.match(content):
            return ShareDataType.URL

        # Detect deep link (scheme:// but not http/https)
        if DEEP_LINK_PATTERN.match(content):
            return ShareDataType.DEEP_LINK

        # Detect image (base64 data URI or image URL)
        if content.startswith("data:image/") or (
            is_http_url(content) and any(content.endswith(ext) for ext in self.IMAGE_EXTENSIONS)
        ):
            return ShareDataType.IMAGE

        return ShareDataType.PLAIN_TEXT

    def _route_to_processor(self, share_data: ShareData) -> BaseShareProcessor:
        """Route share data to appropriate processor."""
        try:
            return self._processors[share_data.data_type]
        except KeyError as e:
            raise UnsupportedShareTypeError(
                f"No processor available for share type: {share_data.data_type.value}"
            ) from e

    async def process_share(self, raw_data: dict) -> ContentMetadata:
        """Process incoming share data and return metadata."""
        share_type = self._identify_share_type(raw_data)

        share_data = ShareData(
            data_type=share_type,
            content=raw_data.get("content", ""),
            metadata=raw_data.get("metadata"),
            source_platform=raw_data.get("platform"),
            options=raw_data.get("options"),
        )

        processor = self._route_to_processor(share_data)
        return await processor.process(share_data)
