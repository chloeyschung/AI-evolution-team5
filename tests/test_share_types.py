"""Tests for share types data structures."""

import pytest

from src.ingestion.share_types import ShareDataType, ShareData


class TestShareDataType:
    """Tests for ShareDataType enum."""

    def test_share_data_type_url(self):
        """Test URL share data type."""
        assert ShareDataType.URL.value == "url"

    def test_share_data_type_plain_text(self):
        """Test plain text share data type."""
        assert ShareDataType.PLAIN_TEXT.value == "plain_text"

    def test_share_data_type_deep_link(self):
        """Test deep link share data type."""
        assert ShareDataType.DEEP_LINK.value == "deep_link"

    def test_share_data_type_image(self):
        """Test image share data type."""
        assert ShareDataType.IMAGE.value == "image"


class TestShareData:
    """Tests for ShareData dataclass."""

    def test_share_data_minimal(self):
        """Test ShareData with required fields only."""
        share_data = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com",
        )

        assert share_data.data_type == ShareDataType.URL
        assert share_data.content == "https://example.com"
        assert share_data.metadata is None
        assert share_data.source_platform is None

    def test_share_data_with_optional_fields(self):
        """Test ShareData with all fields."""
        share_data = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="Some text content",
            metadata={"length": 17},
            source_platform="iOS",
        )

        assert share_data.data_type == ShareDataType.PLAIN_TEXT
        assert share_data.content == "Some text content"
        assert share_data.metadata == {"length": 17}
        assert share_data.source_platform == "iOS"

    def test_share_data_equality(self):
        """Test ShareData equality."""
        data1 = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com",
        )
        data2 = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com",
        )

        assert data1 == data2

    def test_share_data_inequality(self):
        """Test ShareData inequality with different types."""
        data1 = ShareData(
            data_type=ShareDataType.URL,
            content="https://example.com",
        )
        data2 = ShareData(
            data_type=ShareDataType.PLAIN_TEXT,
            content="https://example.com",
        )

        assert data1 != data2
