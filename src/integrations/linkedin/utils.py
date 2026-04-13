"""Utility functions for LinkedIn integration."""

import re
from datetime import datetime, timezone
from typing import Optional


def parse_linkedin_date(date_str: str) -> Optional[datetime]:
    """Parse LinkedIn date string to datetime.

    LinkedIn uses various date formats in their API.

    Args:
        date_str: Date string from LinkedIn API.

    Returns:
        Parsed datetime with UTC timezone, or None if parsing fails.
    """
    if not date_str:
        return None

    # LinkedIn often returns timestamps in milliseconds
    if date_str.isdigit():
        try:
            timestamp = int(date_str) / 1000  # Convert ms to seconds
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, OSError):
            return None

    # Try ISO format
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return None


def extract_post_id_from_url(url: str) -> Optional[str]:
    """Extract post ID from LinkedIn URL.

    Args:
        url: LinkedIn post URL.

    Returns:
        Post ID if found, None otherwise.
    """
    # Pattern for LinkedIn post URLs
    patterns = [
        r"/feed/update/urn:li:(share|activity):([a-zA-Z0-9_-]+)/?",
        r"/posts/([a-zA-Z0-9_-]+)/?",
        r"/pulse/([a-zA-Z0-9_-]+)/?",
        r"/detail/([a-zA-Z0-9_-]+)/?",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # Return the last captured group (the ID)
            return match.group(len(match.groups()))

    return None


def normalize_linkedin_urn(urn: str) -> str:
    """Normalize LinkedIn URN to standard format.

    Args:
        urn: LinkedIn URN (may be in various formats).

    Returns:
        Normalized URN.
    """
    if not urn:
        return ""

    # Remove whitespace
    urn = urn.strip()

    # Ensure URN starts with urn:li:
    if not urn.startswith("urn:li:"):
        # Try to prefix if it looks like a LinkedIn ID
        if urn.startswith("share:") or urn.startswith("activity:"):
            urn = "urn:li:" + urn
        elif not urn.startswith("http"):
            # Assume it's a raw ID and prefix with share
            urn = f"urn:li:share:{urn}"

    return urn


def is_linkedin_url(url: str) -> bool:
    """Check if URL is a LinkedIn URL.

    Args:
        url: URL to check.

    Returns:
        True if LinkedIn URL, False otherwise.
    """
    linkedin_domains = [
        "linkedin.com",
        "www.linkedin.com",
        "lnkd.in",  # LinkedIn short URLs
    ]

    return any(domain in url.lower() for domain in linkedin_domains)
