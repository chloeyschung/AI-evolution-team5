import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.ingestion.extractor import ContentExtractor
from src.ingestion.exceptions import ExtractionError

@pytest.fixture
def extractor():
    return ContentExtractor(timeout=1.0)

@pytest.mark.asyncio
async def test_extract_text_invalid_url_format(extractor):
    # Test invalid URL formats
    invalid_urls = [
        "",
        "not-a-url",
        "ftp://example.com",
        "http://",
        "example.com",  # missing scheme
    ]

    for invalid_url in invalid_urls:
        with pytest.raises(ExtractionError, match="Invalid URL format|URL must be a non-empty string"):
            await extractor.extract_text(invalid_url)

@pytest.mark.asyncio
async def test_extract_text_exceeds_size_limit(extractor):
    # Create content larger than MAX_CONTENT_SIZE
    large_html = "<html><body>" + "x" * (ContentExtractor.MAX_CONTENT_SIZE + 1) + "</body></html>"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = large_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(ExtractionError, match="exceeds maximum size limit"):
            await extractor.extract_text("https://example.com/large")


@pytest.mark.asyncio
async def test_extract_text_success(extractor):
    # Mocking the httpx response with valid HTML content
    mock_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <header><h1>Header</h1></header>
            <nav><ul><li>Link</li></ul></nav>
            <article>
                <h2>Article Title</h2>
                <p>This is the main content of the article.</p>
                <p>It has multiple lines.</p>
            </article>
            <footer>Footer info</footer>
            <script>console.log('noise');</script>
        </body>
    </html>
    """

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await extractor.extract_text("https://example.com/article")

        assert "Article Title" in result
        assert "This is the main content of the article." in result
        assert "It has multiple lines." in result
        assert "Header" not in result
        assert "Footer info" not in result
        assert "Link" not in result
        assert "console.log" not in result

@pytest.mark.asyncio
async def test_extract_text_http_error(extractor):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(ExtractionError, match="HTTP error occurred: 404"):
            await extractor.extract_text("https://example.com/404")

@pytest.mark.asyncio
async def test_extract_text_invalid_url(extractor):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("Connection error", request=MagicMock())

        with pytest.raises(ExtractionError, match="An error occurred while requesting"):
            await extractor.extract_text("https://invalid-url.com")

@pytest.mark.asyncio
async def test_extract_text_empty_content(extractor):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(ExtractionError, match="Received empty HTML content"):
            await extractor.extract_text("https://example.com/empty")

@pytest.mark.asyncio
async def test_extract_text_no_meaningful_content(extractor):
    mock_html = "<html><head></head><body><script>alert(1)</script></body></html>"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(ExtractionError, match="Extracted text is empty"):
            await extractor.extract_text("https://example.com/noise")