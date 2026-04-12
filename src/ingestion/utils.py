"""Utility functions and constants for ingestion module."""

import re
from urllib.parse import urlparse

from .exceptions import InvalidShareDataError

# URL validation pattern (requires http(s):// + domain)
URL_VALIDATION_PATTERN = re.compile(
    r'^https?:\/\/'  # http or https
    r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # domain
    r'(\/[^\s]*)?$'  # optional path
)

# URL extraction pattern (matches URLs in text, including www.)
URL_EXTRACTION_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
)

# URL detection pattern (full match, for identifying URL share data)
URL_DETECTION_PATTERN = re.compile(
    r'^https?://[^\s<>"{}|\\^`\[\]]+$|^www\.[^\s<>"{}|\\^`\[\]]+$'
)

# Deep link pattern (scheme:// but not http/https)
DEEP_LINK_PATTERN = re.compile(r'^[a-z][a-z0-9+.-]*://[^\s]+$')


def validate_non_empty(content: str, error_msg: str) -> str:
    """Validate content is non-empty after stripping whitespace.

    Args:
        content: The content to validate.
        error_msg: Error message to raise if validation fails.

    Returns:
        The stripped content.

    Raises:
        InvalidShareDataError: If content is empty after stripping.
    """
    stripped = content.strip()
    if not stripped:
        raise InvalidShareDataError(error_msg)
    return stripped


def is_http_url(data: str) -> bool:
    """Check if data is an HTTP/HTTPS URL.

    Args:
        data: The string to check.

    Returns:
        True if data starts with http:// or https://.
    """
    return data.startswith(("http://", "https://"))


def extract_scheme(url: str) -> str:
    """Extract the scheme from a URL or deep link.

    Args:
        url: The URL or deep link string.

    Returns:
        The lowercase scheme (e.g., "https", "whatsapp", "mailto").
    """
    return urlparse(url).scheme.lower()
