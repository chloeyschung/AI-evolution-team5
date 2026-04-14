import ipaddress
import re
from urllib.parse import urlparse
from urllib.parse import urldefrag

import httpx
from bs4 import BeautifulSoup
from .exceptions import ExtractionError
from src.utils.http_client import async_client_context

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
        Validates the URL format and checks for SSRF vulnerabilities.

        Args:
            url: The URL to validate.

        Raises:
            ExtractionError: If the URL is invalid or points to a restricted resource.
        """
        if not url or not isinstance(url, str):
            raise ExtractionError("URL must be a non-empty string.")

        url = url.strip()

        # Check URL pattern
        if not self.URL_PATTERN.match(url):
            raise ExtractionError(f"Invalid URL format: {url}")

        # Check scheme
        parsed = urlparse(urldefrag(url)[0])  # Remove fragment before parsing
        if parsed.scheme not in ('http', 'https'):
            raise ExtractionError(f"URL must use http or https scheme: {url}")

        # SSRF protection: block access to internal/private IP ranges
        if parsed.hostname:
            self._check_ssrf(parsed.hostname)

    def _check_ssrf(self, hostname: str) -> None:
        """
        Check if hostname resolves to a private/internal IP address.

        Args:
            hostname: The hostname to check.

        Raises:
            ExtractionError: If the hostname resolves to a restricted IP.
        """
        import socket

        # Block common internal hostnames
        internal_hostnames = {
            'localhost', 'localhost.localdomain', 'local',
            'internal', 'intranet', 'private'
        }

        if hostname.lower() in internal_hostnames:
            raise ExtractionError(f"Access to internal hostname blocked: {hostname}")

        # Block IP literals (prevent direct IP access)
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ExtractionError(f"Access to private/reserved IP address blocked: {hostname}")
        except ValueError:
            # Not an IP address, will resolve and check below (DNS rebinding protection)
            pass

        # Resolve hostname and check resolved IPs (DNS rebinding protection)
        # This prevents attacks where a hostname initially passes checks but resolves to private IPs
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for info in resolved_ips:
                resolved_ip = info[4][0]
                try:
                    ipaddr = ipaddress.ip_address(resolved_ip)
                    if ipaddr.is_private or ipaddr.is_loopback or ipaddr.is_link_local or ipaddr.is_reserved:
                        raise ExtractionError(
                            f"Hostname resolves to private/reserved IP: {resolved_ip}"
                        )
                except ValueError:
                    # Unexpected IP format, skip
                    continue
        except socket.gaierror:
            # DNS resolution failed - this is acceptable, will fail during actual fetch if needed
            pass

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
            async with async_client_context(follow_redirects=True) as client:
                response = await client.get(url, timeout=self.timeout)
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