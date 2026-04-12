import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from .exceptions import ExtractionError

class ContentExtractor:
    """Extracts clean text content from web URLs."""

    # URL pattern for basic validation
    URL_PATTERN = re.compile(
        r'^https?:\/\/'  # http or https
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # domain
        r'(\/[^\s]*)?$'  # optional path
    )

    # Maximum content size (10MB)
    MAX_CONTENT_SIZE = 10 * 1024 * 1024

    # Tags to remove during content extraction
    TAGS_TO_REMOVE = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def _validate_url(self, url: str) -> None:
        """
        Validates the URL format.

        Args:
            url: The URL to validate.

        Raises:
            ExtractionError: If the URL is invalid.
        """
        if not url or not isinstance(url, str):
            raise ExtractionError("URL must be a non-empty string.")

        url = url.strip()

        # Check URL pattern
        if not self.URL_PATTERN.match(url):
            raise ExtractionError(f"Invalid URL format: {url}")

        # Check scheme
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ExtractionError(f"URL must use http or https scheme: {url}")

    async def extract_text(self, url: str) -> str:
        """
        Fetches a URL and extracts its primary text content.

        Args:
            url: The URL to extract content from.

        Returns:
            A cleaned string of the main text content.

        Raises:
            ExtractionError: If the URL is invalid, unreachable, or contains no text.
        """
        # Validate URL format first
        self._validate_url(url)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"HTTP error occurred: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ExtractionError(f"An error occurred while requesting {url}: {e}") from e
        except Exception as e:
            raise ExtractionError(f"An unexpected error occurred during fetch: {e}") from e

        html_content = response.text

        # Check content size
        if len(html_content) > self.MAX_CONTENT_SIZE:
            raise ExtractionError(f"Content exceeds maximum size limit of {self.MAX_CONTENT_SIZE} bytes.")

        if not html_content:
            raise ExtractionError("Received empty HTML content from the URL.")

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove non-content tags
            for tag in soup(self.TAGS_TO_REMOVE):
                tag.decompose()

            # Identify the main content container
            main_content = soup.find(['article', 'main', 'body'])

            if not main_content:
                raise ExtractionError("Could not find any meaningful content container.")

            # Extract text
            text = main_content.get_text(separator=' ')

            # Clean the text: remove excessive whitespace, normalize line breaks
            clean_text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())

            if not clean_text:
                raise ExtractionError("Extracted text is empty.")

            return clean_text

        except Exception as e:
            raise ExtractionError(f"An error occurred during parsing: {e}") from e