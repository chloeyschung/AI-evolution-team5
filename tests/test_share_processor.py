"""Tests for share data processors."""

import pytest

from src.ai.metadata_extractor import ContentMetadata
from src.constants import ContentType
from src.ingestion.share_processor import (
    URLShareProcessor,
    PlainTextProcessor,
    DeepLinkProcessor,
    ImageProcessor,
)
from src.ingestion.share_types import ShareDataType, ShareData
from src.ingestion.exceptions import (
    InvalidShareDataError,
    DeepLinkValidationError,
    ImageProcessingError,
)


class TestURLShareProcessor:
    """Tests for URLShareProcessor."""

    @pytest.mark.asyncio
    async def test_process_valid_url(self, content_extractor_mock, metadata_extractor_mock):
        """Test processing a valid URL."""
        processor = URLShareProcessor(content_extractor_mock, metadata_extractor_mock)
        share_data = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com/article",
        )

        metadata = await processor.process(share_data)

        metadata_extractor_mock.extract_metadata.assert_called_once()
        assert metadata.platform == "Test"

    @pytest.mark.asyncio
    async def test_process_empty_url(self, content_extractor_mock, metadata_extractor_mock):
        """Test processing an empty URL raises error."""
        processor = URLShareProcessor(content_extractor_mock, metadata_extractor_mock)
        share_data = ShareData(
            data_type=ShareDataType.URL,
            content="   ",
        )

        with pytest.raises(InvalidShareDataError, match="URL content is empty"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_supported_types(self, content_extractor_mock, metadata_extractor_mock):
        """Test that processor supports URL type."""
        processor = URLShareProcessor(content_extractor_mock, metadata_extractor_mock)
        assert processor.supported_types == [ShareDataType.URL]


class TestPlainTextProcessor:
    """Tests for PlainTextProcessor."""

    @pytest.mark.asyncio
    async def test_process_short_text(self):
        """Test processing short plain text."""
        processor = PlainTextProcessor()
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="This is a short note",
        )

        metadata = await processor.process(share_data)

        assert metadata.platform == "clipboard"
        assert metadata.content_type == ContentType.ARTICLE
        assert metadata.title == "This is a short note"

    @pytest.mark.asyncio
    async def test_process_text_with_embedded_url(self):
        """Test processing text containing a URL."""
        processor = PlainTextProcessor()
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="Check this out: https://example.com/article",
        )

        metadata = await processor.process(share_data)

        assert metadata.url == "https://example.com/article"
        assert metadata.content_type == ContentType.ARTICLE

    @pytest.mark.asyncio
    async def test_process_text_with_www_url(self):
        """Test processing text containing www URL."""
        processor = PlainTextProcessor()
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="Visit www.example.com for more",
        )

        metadata = await processor.process(share_data)

        assert metadata.url == "www.example.com"

    @pytest.mark.asyncio
    async def test_process_empty_text(self):
        """Test processing empty text raises error."""
        processor = PlainTextProcessor()
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="   ",
        )

        with pytest.raises(InvalidShareDataError, match="Plain text content is empty"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_process_long_text_truncates_title(self):
        """Test that long text titles are truncated."""
        processor = PlainTextProcessor()
        long_text = "A" * 200
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content=long_text,
        )

        metadata = await processor.process(share_data)

        assert len(metadata.title) == 100

    @pytest.mark.asyncio
    async def test_supported_types(self):
        """Test that processor supports plain text type."""
        processor = PlainTextProcessor()
        assert processor.supported_types == [ShareDataType.PLAIN_TEXT]


class TestDeepLinkProcessor:
    """Tests for DeepLinkProcessor."""

    @pytest.mark.asyncio
    async def test_process_whatsapp_deep_link(self):
        """Test processing WhatsApp deep link."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="whatsapp://send?text=Hello",
        )

        metadata = await processor.process(share_data)

        assert metadata.platform == "Whatsapp"
        assert metadata.content_type == ContentType.SOCIAL_POST

    @pytest.mark.asyncio
    async def test_process_telegram_deep_link(self):
        """Test processing Telegram deep link."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="tg://resolve?domain=username",
        )

        metadata = await processor.process(share_data)

        assert metadata.platform == "Telegram"
        assert metadata.content_type == ContentType.SOCIAL_POST

    @pytest.mark.asyncio
    async def test_process_mailto_deep_link(self):
        """Test processing mailto deep link."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="mailto:test@example.com",
        )

        metadata = await processor.process(share_data)

        assert metadata.platform == "Mailto"
        assert metadata.content_type == ContentType.ARTICLE

    @pytest.mark.asyncio
    async def test_process_video_deep_link(self):
        """Test processing video deep link."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="youtube://watch?v=abc123",
        )

        metadata = await processor.process(share_data)

        assert metadata.content_type == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_process_empty_deep_link(self):
        """Test processing empty deep link raises error."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="   ",
        )

        with pytest.raises(InvalidShareDataError, match="Deep link content is empty"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_process_invalid_deep_link(self):
        """Test processing invalid deep link raises error."""
        processor = DeepLinkProcessor()
        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="not-a-deep-link",
        )

        with pytest.raises(DeepLinkValidationError, match="Invalid deep link format"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_supported_types(self):
        """Test that processor supports deep link type."""
        processor = DeepLinkProcessor()
        assert processor.supported_types == [ShareDataType.DEEP_LINK]


class TestImageProcessor:
    """Tests for ImageProcessor."""

    @pytest.mark.asyncio
    async def test_process_base64_image(self):
        """Test processing base64 encoded image."""
        processor = ImageProcessor()
        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )

        metadata = await processor.process(share_data)

        assert metadata.content_type == ContentType.IMAGE
        assert metadata.url == ""

    @pytest.mark.asyncio
    async def test_process_image_url(self):
        """Test processing image URL."""
        processor = ImageProcessor()
        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="https://example.com/image.jpg",
        )

        metadata = await processor.process(share_data)

        assert metadata.content_type == ContentType.IMAGE
        assert metadata.url == "https://example.com/image.jpg"

    @pytest.mark.asyncio
    async def test_process_file_path(self):
        """Test processing image file path."""
        processor = ImageProcessor()
        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="/path/to/image.png",
            source_platform="iOS",
        )

        metadata = await processor.process(share_data)

        assert metadata.content_type == ContentType.IMAGE
        assert metadata.platform == "iOS"

    @pytest.mark.asyncio
    async def test_process_empty_image(self):
        """Test processing empty image raises error."""
        processor = ImageProcessor()
        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="   ",
        )

        with pytest.raises(InvalidShareDataError, match="Image content is empty"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_process_invalid_image_data(self):
        """Test processing invalid image data raises error."""
        processor = ImageProcessor()
        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="not-an-image",
        )

        with pytest.raises(ImageProcessingError, match="Invalid image data format"):
            await processor.process(share_data)

    @pytest.mark.asyncio
    async def test_supported_types(self):
        """Test that processor supports image type."""
        processor = ImageProcessor()
        assert processor.supported_types == [ShareDataType.IMAGE]
