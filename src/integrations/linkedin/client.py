"""LinkedIn API client with OAuth 2.0 support."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from ...ai.metadata_extractor import MetadataExtractor
from .models import LinkedInPost, LinkedInSavedItem
from src.utils.http_client import async_client_context
from src.utils.datetime_utils import utc_now


class LinkedInClientError(Exception):
    """Base exception for LinkedIn client errors."""
    pass


class LinkedInAuthError(LinkedInClientError):
    """Authentication/authorization error."""
    pass


class LinkedInRateLimitError(LinkedInClientError):
    """Rate limit exceeded error."""
    pass


class LinkedInAPIError(LinkedInClientError):
    """General API error."""
    pass


class LinkedInClient:
    """LinkedIn API client with OAuth 2.0 support."""

    BASE_URL = "https://api.linkedin.com/v2"
    DEFAULT_LINKEDIN_URL = "https://www.linkedin.com"

    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        """Initialize LinkedIn client.

        Args:
            access_token: LinkedIn OAuth access token.
            refresh_token: Optional refresh token for token rotation.
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._metadata_extractor = MetadataExtractor()

    async def get_saved_items(self, count: int = 50) -> list[LinkedInSavedItem]:
        """Get user's saved items from LinkedIn.

        Args:
            count: Maximum number of items to fetch.

        Returns:
            List of saved items.

        Raises:
            LinkedInAuthError: If authentication fails.
            LinkedInRateLimitError: If rate limit exceeded.
            LinkedInAPIError: If API call fails.
        """
        # Note: LinkedIn API for saved items requires specific permissions
        # This is a placeholder implementation - actual API endpoint may vary
        # LinkedIn's saved items API: GET /v2/me/savedItems
        async with async_client_context() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Linkedin-Version": "202401",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            try:
                # Placeholder: LinkedIn saved items endpoint
                # Actual implementation requires LinkedIn Developer App approval
                response = await client.get(
                    f"{self.BASE_URL}/me/savedItems",
                    headers=headers,
                    params={"count": count},
                    timeout=30.0,
                )

                if response.status_code == 401:
                    raise LinkedInAuthError("Invalid or expired access token")
                if response.status_code == 429:
                    raise LinkedInRateLimitError("Rate limit exceeded")
                if response.status_code != 200:
                    raise LinkedInAPIError(f"API error: {response.status_code} - {response.text}")

                data = response.json()
                return self._parse_saved_items(data)

            except httpx.RequestError as e:
                raise LinkedInAPIError(f"Request failed: {e}")

    def _parse_saved_items(self, data: dict) -> list[LinkedInSavedItem]:
        """Parse saved items from API response.

        Args:
            data: Raw API response data.

        Returns:
            List of parsed saved items.
        """
        items = []
        elements = data.get("elements", [])

        for element in elements:
            try:
                item = LinkedInSavedItem(
                    urn=element.get("urn", ""),
                    saved_at=datetime.fromisoformat(
                        element.get("savedAt", utc_now().isoformat())
                    ).replace(tzinfo=timezone.utc),
                    target_urn=element.get("target", {}).get("urn", ""),
                )
                items.append(item)
            except (KeyError, ValueError) as e:
                # Skip malformed items
                continue

        return items

    async def get_post_from_url(self, url: str) -> Optional[LinkedInPost]:
        """Extract post data from a LinkedIn URL.

        This method fetches the page and extracts metadata.
        It works without API access by parsing the public page.

        Args:
            url: LinkedIn post URL.

        Returns:
            LinkedInPost if found, None otherwise.
        """
        try:
            # Use metadata extractor to get post data from HTML
            async with async_client_context() as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code != 200:
                    return None

                html_content = response.text

                # Extract metadata using existing extractor
                metadata = await self._metadata_extractor.extract_metadata(url, html_content)

                # Extract URN from URL
                urn = self._extract_urn_from_url(url)

                return LinkedInPost(
                    urn=urn or url,
                    url=url,
                    title=metadata.title or "LinkedIn Post",
                    author=metadata.author or "Unknown",
                    author_urn=urn or "",
                    published_at=metadata.timestamp,
                    content_type=metadata.content_type.value,
                    image_url=metadata.thumbnail_url,
                )

        except Exception:
            return None

    def _extract_urn_from_url(self, url: str) -> Optional[str]:
        """Extract LinkedIn URN from URL.

        Args:
            url: LinkedIn post URL.

        Returns:
            URN if found, None otherwise.
        """
        # LinkedIn URLs typically contain URN in the format:
        # https://www.linkedin.com/feed/update/urn:li:share:1234567890/
        if "urn:li:" in url:
            start = url.find("urn:li:")
            end = url.find("/", start)
            if end == -1:
                end = len(url)
            return url[start:end]
        return None

    def generate_post_url(self, urn: str) -> str:
        """Generate a public LinkedIn post URL from URN.

        Args:
            urn: LinkedIn URN (e.g., urn:li:share:1234567890).

        Returns:
            Public URL to the post.
        """
        # Convert URN to public URL format
        if urn.startswith("urn:li:share:"):
            post_id = urn.replace("urn:li:share:", "")
            return f"{self.DEFAULT_LINKEDIN_URL}/feed/update/urn:li:share:{post_id}/"
        elif urn.startswith("urn:li:activity:"):
            activity_id = urn.replace("urn:li:activity:", "")
            return f"{self.DEFAULT_LINKEDIN_URL}/feed/update/urn:li:activity:{activity_id}/"
        return urn  # Return as-is if already a URL
