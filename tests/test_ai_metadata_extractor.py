"""Tests for AI-002: Multi-Modal Metadata Extraction."""

import pytest
from datetime import datetime

from src.ai.metadata_extractor import MetadataExtractor, ContentMetadata, ContentType
from src.ai.exceptions import InvalidURLError


@pytest.fixture
def extractor():
    return MetadataExtractor()


class TestURLParsing:
    """Tests for URL parsing and validation."""

    @pytest.mark.asyncio
    async def test_extract_metadata_youtube_video(self, extractor):
        """Test YouTube video URL extraction."""
        url = "https://www.youtube.com/watch?v=abc123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "YouTube"
        assert metadata.content_type == ContentType.VIDEO
        assert metadata.url == url

    @pytest.mark.asyncio
    async def test_extract_metadata_youtube_shorts(self, extractor):
        """Test YouTube Shorts URL extraction."""
        url = "https://www.youtube.com/shorts/xyz789"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "YouTube"
        assert metadata.content_type == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_extract_metadata_youtube_short_url(self, extractor):
        """Test YouTube short URL extraction."""
        url = "https://youtu.be/abc123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "YouTube"
        assert metadata.content_type == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_extract_metadata_linkedin_post(self, extractor):
        """Test LinkedIn post URL extraction."""
        url = "https://www.linkedin.com/post/abc123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "LinkedIn"
        assert metadata.content_type == ContentType.SOCIAL_POST

    @pytest.mark.asyncio
    async def test_extract_metadata_linkedin_article(self, extractor):
        """Test LinkedIn article URL extraction."""
        url = "https://www.linkedin.com/pulse/article-title-author"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "LinkedIn"
        assert metadata.content_type == ContentType.ARTICLE

    @pytest.mark.asyncio
    async def test_extract_metadata_medium_article(self, extractor):
        """Test Medium article URL extraction."""
        url = "https://medium.com/@author/article-title-abc123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Medium"
        assert metadata.content_type == ContentType.ARTICLE

    @pytest.mark.asyncio
    async def test_extract_metadata_twitter_post(self, extractor):
        """Test Twitter/X post URL extraction."""
        url = "https://twitter.com/user/status/123456789"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Twitter/X"
        assert metadata.content_type == ContentType.SOCIAL_POST

    @pytest.mark.asyncio
    async def test_extract_metadata_x_com_post(self, extractor):
        """Test x.com post URL extraction."""
        url = "https://x.com/user/status/123456789"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Twitter/X"
        assert metadata.content_type == ContentType.SOCIAL_POST

    @pytest.mark.asyncio
    async def test_extract_metadata_instagram_image(self, extractor):
        """Test Instagram image URL extraction."""
        url = "https://www.instagram.com/p/abc123/"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Instagram"
        assert metadata.content_type == ContentType.IMAGE

    @pytest.mark.asyncio
    async def test_extract_metadata_instagram_reel(self, extractor):
        """Test Instagram Reel URL extraction."""
        url = "https://www.instagram.com/reel/xyz789/"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Instagram"
        assert metadata.content_type == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_extract_metadata_unknown_domain(self, extractor):
        """Test unknown domain URL extraction."""
        url = "https://randomblog.com/post/123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "Randomblog"
        assert metadata.content_type == ContentType.ARTICLE


class TestHTMLExtraction:
    """Tests for HTML content metadata extraction."""

    @pytest.mark.asyncio
    async def test_extract_timestamp_from_time_tag(self, extractor):
        """Test timestamp extraction from <time> tag."""
        url = "https://example.com/article"
        html = """
        <html>
        <body>
            <article>
                <time datetime="2024-01-15T10:30:00Z">January 15, 2024</time>
                <p>Article content</p>
            </article>
        </body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.timestamp is not None
        assert metadata.timestamp.year == 2024
        assert metadata.timestamp.month == 1
        assert metadata.timestamp.day == 15

    @pytest.mark.asyncio
    async def test_extract_timestamp_from_meta_tag(self, extractor):
        """Test timestamp extraction from meta tag."""
        url = "https://example.com/article"
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2024-03-20T14:00:00Z">
        </head>
        <body>Article content</body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.timestamp is not None
        assert metadata.timestamp.year == 2024
        assert metadata.timestamp.month == 3
        assert metadata.timestamp.day == 20

    @pytest.mark.asyncio
    async def test_extract_author_from_meta_tag(self, extractor):
        """Test author extraction from meta tag."""
        url = "https://example.com/article"
        html = """
        <html>
        <head>
            <meta property="article:author" content="John Doe">
        </head>
        <body>Article content</body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.author == "John Doe"

    @pytest.mark.asyncio
    async def test_extract_title_from_og_tag(self, extractor):
        """Test title extraction from og:title meta tag."""
        url = "https://example.com/article"
        html = """
        <html>
        <head>
            <meta property="og:title" content="My Article Title">
        </head>
        <body>Article content</body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.title == "My Article Title"

    @pytest.mark.asyncio
    async def test_extract_title_from_title_tag(self, extractor):
        """Test title extraction from <title> tag."""
        url = "https://example.com/article"
        html = """
        <html>
        <head>
            <title>My Article Title</title>
        </head>
        <body>Article content</body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.title == "My Article Title"

    @pytest.mark.asyncio
    async def test_extract_full_metadata(self, extractor):
        """Test extraction of all metadata fields."""
        url = "https://medium.com/@author/article-abc123"
        html = """
        <html>
        <head>
            <meta property="og:title" content="Understanding AI">
            <meta property="article:author" content="Jane Smith">
            <meta property="article:published_time" content="2024-06-01T09:00:00Z">
        </head>
        <body>Article content</body>
        </html>
        """
        metadata = await extractor.extract_metadata(url, html)

        assert metadata.platform == "Medium"
        assert metadata.content_type == ContentType.ARTICLE
        assert metadata.title == "Understanding AI"
        assert metadata.author == "Jane Smith"
        assert metadata.timestamp is not None
        assert metadata.timestamp.year == 2024


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_extract_metadata_empty_url(self, extractor):
        """Test extraction with empty URL."""
        with pytest.raises(InvalidURLError, match="URL must be a non-empty string"):
            await extractor.extract_metadata("")

    @pytest.mark.asyncio
    async def test_extract_metadata_invalid_url(self, extractor):
        """Test extraction with invalid URL."""
        with pytest.raises(InvalidURLError, match="Invalid URL format"):
            await extractor.extract_metadata("not-a-url")

    @pytest.mark.asyncio
    async def test_extract_metadata_url_only(self, extractor):
        """Test extraction with URL only (no HTML content)."""
        url = "https://youtube.com/watch?v=abc123"
        metadata = await extractor.extract_metadata(url)

        assert metadata.platform == "YouTube"
        assert metadata.content_type == ContentType.VIDEO
        assert metadata.timestamp is None
        assert metadata.author is None


class TestContentMetadata:
    """Tests for ContentMetadata class."""

    def test_metadata_to_dict(self):
        """Test conversion to dictionary."""
        metadata = ContentMetadata(
            platform="YouTube",
            content_type=ContentType.VIDEO,
            url="https://youtube.com/watch?v=abc",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            author="Test Author",
            title="Test Title",
        )

        result = metadata.to_dict()

        assert result["platform"] == "YouTube"
        assert result["content_type"] == "video"
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert result["author"] == "Test Author"
        assert result["title"] == "Test Title"

    def test_metadata_to_dict_without_optional_fields(self):
        """Test conversion with missing optional fields."""
        metadata = ContentMetadata(
            platform="Web",
            content_type=ContentType.ARTICLE,
            url="https://example.com",
        )

        result = metadata.to_dict()

        assert result["timestamp"] is None
        assert result["author"] is None
        assert result["title"] is None
