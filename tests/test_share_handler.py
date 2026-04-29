"""Tests for ShareHandler integration."""

import pytest

from src.constants import ContentType
from src.ingestion.share_handler import ShareHandler
from src.ingestion.share_types import ShareDataType, ShareData
from src.ingestion.exceptions import (
    InvalidShareDataError,
    UnsupportedShareTypeError,
)


@pytest.fixture
def share_handler(content_extractor_mock, metadata_extractor_mock_testplatform):
    """Create ShareHandler with mocked dependencies."""
    return ShareHandler(content_extractor_mock, metadata_extractor_mock_testplatform)


class TestIdentifyShareType:
    """Tests for share type identification."""

    def test_identify_url(self, share_handler):
        """Test URL identification."""
        raw_data = {"content": "https://example.com/article"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.URL

    def test_identify_http_url(self, share_handler):
        """Test HTTP URL identification."""
        raw_data = {"content": "http://example.com/article"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.URL

    def test_identify_www_url(self, share_handler):
        """Test www URL identification."""
        raw_data = {"content": "www.example.com/article"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.URL

    def test_identify_deep_link(self, share_handler):
        """Test deep link identification."""
        raw_data = {"content": "whatsapp://send?text=hello"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.DEEP_LINK

    def test_identify_twitter_deep_link(self, share_handler):
        """Test Twitter deep link identification."""
        raw_data = {"content": "twitter://post?id=123"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.DEEP_LINK

    def test_identify_image_base64(self, share_handler):
        """Test base64 image identification."""
        raw_data = {"content": "data:image/png;base64,abc123"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.IMAGE

    def test_identify_image_url(self, share_handler):
        """Test image URL identification."""
        raw_data = {"content": "https://example.com/photo.jpg"}
        # Note: This will be identified as URL due to pattern matching priority
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.URL

    def test_identify_plain_text(self, share_handler):
        """Test plain text identification."""
        raw_data = {"content": "This is just some text"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.PLAIN_TEXT

    def test_identify_explicit_type(self, share_handler):
        """Test explicit type override."""
        raw_data = {"content": "https://example.com", "type": "plain_text"}
        share_type = share_handler._identify_share_type(raw_data)
        assert share_type == ShareDataType.PLAIN_TEXT

    def test_identify_missing_content(self, share_handler):
        """Test missing content raises error."""
        raw_data = {}
        with pytest.raises(InvalidShareDataError, match="must contain 'content' field"):
            share_handler._identify_share_type(raw_data)

    def test_identify_empty_content(self, share_handler):
        """Test empty content raises error."""
        raw_data = {"content": ""}
        with pytest.raises(InvalidShareDataError, match="cannot be empty"):
            share_handler._identify_share_type(raw_data)

    def test_identify_not_dict(self, share_handler):
        """Test non-dict input raises error."""
        with pytest.raises(InvalidShareDataError, match="must be a dictionary"):
            share_handler._identify_share_type("not a dict")


class TestProcessShare:
    """Tests for share processing."""

    @pytest.mark.asyncio
    async def test_process_url_share(self, share_handler, metadata_extractor_mock_testplatform):
        """Test processing URL share."""
        raw_data = {"content": "https://example.com/article"}
        metadata = await share_handler.process_share(raw_data)

        assert metadata.platform == "TestPlatform"
        metadata_extractor_mock_testplatform.extract_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_text_share(self, share_handler):
        """Test processing plain text share."""
        raw_data = {"content": "My note: important meeting at 3pm"}
        metadata = await share_handler.process_share(raw_data)

        assert metadata.platform == "clipboard"
        assert metadata.content_type == ContentType.ARTICLE

    @pytest.mark.asyncio
    async def test_process_deep_link_share(self, share_handler):
        """Test processing deep link share."""
        raw_data = {"content": "tg://resolve?domain=username"}
        metadata = await share_handler.process_share(raw_data)

        assert metadata.url == "tg://resolve?domain=username"

    @pytest.mark.asyncio
    async def test_process_share_with_platform(self, share_handler):
        """Test processing share with source platform."""
        raw_data = {
            "content": "data:image/png;base64,abc",
            "platform": "iOS",
        }
        metadata = await share_handler.process_share(raw_data)

        assert metadata.platform == "iOS"

    @pytest.mark.asyncio
    async def test_process_share_with_metadata(self, share_handler):
        """Test processing share with additional metadata."""
        raw_data = {
            "content": "https://example.com",
            "metadata": {"shared_at": "2024-01-15T10:30:00Z"},
        }
        # Metadata is passed through ShareData but may not be used in final ContentMetadata
        metadata = await share_handler.process_share(raw_data)

        assert metadata is not None


class TestRouteToProcessor:
    """Tests for processor routing."""

    def test_route_url_processor(self, share_handler):
        """Test routing to URL processor."""
        from src.ingestion.share_processor import URLShareProcessor

        share_data = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com",
        )
        processor = share_handler._route_to_processor(share_data)
        assert isinstance(processor, URLShareProcessor)

    def test_route_text_processor(self, share_handler):
        """Test routing to plain text processor."""
        from src.ingestion.share_processor import PlainTextProcessor

        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="Some text",
        )
        processor = share_handler._route_to_processor(share_data)
        assert isinstance(processor, PlainTextProcessor)

    def test_route_deep_link_processor(self, share_handler):
        """Test routing to deep link processor."""
        from src.ingestion.share_processor import DeepLinkProcessor

        share_data = ShareData(
            data_type=ShareDataType.DEEP_LINK,
            content="tg://msg",
        )
        processor = share_handler._route_to_processor(share_data)
        assert isinstance(processor, DeepLinkProcessor)

    def test_route_image_processor(self, share_handler):
        """Test routing to image processor."""
        from src.ingestion.share_processor import ImageProcessor

        share_data = ShareData(
            data_type=ShareDataType.IMAGE,
            content="data:image/png;base64,abc",
        )
        processor = share_handler._route_to_processor(share_data)
        assert isinstance(processor, ImageProcessor)
