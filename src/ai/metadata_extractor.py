"""Multi-Modal Metadata Extraction service for Briefly."""

from datetime import datetime
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser
from urllib.parse import urlparse, ParseResult

from .exceptions import InvalidURLError


class ContentType(Enum):
    """Supported content types for metadata."""

    ARTICLE = "article"
    VIDEO = "video"
    IMAGE = "image"
    SOCIAL_POST = "social_post"
    PROFILE = "profile"
    DEEP_LINK = "deep_link"


class ContentMetadata:
    """Structured metadata extracted from content."""

    def __init__(
        self,
        platform: str,
        content_type: ContentType,
        url: str,
        timestamp: Optional[datetime] = None,
        author: Optional[str] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        self.platform = platform
        self.content_type = content_type
        self.url = url
        self.timestamp = timestamp
        self.author = author
        self.title = title
        self.summary = summary

    def __repr__(self) -> str:
        return (
            f"ContentMetadata(platform={self.platform!r}, content_type={self.content_type.value!r}, "
            f"url={self.url!r}, timestamp={self.timestamp}, author={self.author!r}, title={self.title!r})"
        )

    def to_dict(self) -> dict:
        """Convert metadata to dictionary format."""
        return {
            "platform": self.platform,
            "content_type": self.content_type.value,
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "author": self.author,
            "title": self.title,
            "summary": self.summary,
        }


class MetadataExtractor:
    """Extracts metadata from URLs and HTML content."""

    PLATFORM_MAPPING = {
        "youtube.com": ("YouTube", {"/watch": ContentType.VIDEO, "/shorts": ContentType.VIDEO, "/live": ContentType.VIDEO}),
        "youtu.be": ("YouTube", {"": ContentType.VIDEO}),
        "linkedin.com": ("LinkedIn", {"/post/": ContentType.SOCIAL_POST, "/pulse/": ContentType.ARTICLE, "/article/": ContentType.ARTICLE, "/in/": ContentType.PROFILE}),
        "medium.com": ("Medium", {"/": ContentType.ARTICLE}),
        "twitter.com": ("Twitter/X", {"/status/": ContentType.SOCIAL_POST}),
        "x.com": ("Twitter/X", {"/status/": ContentType.SOCIAL_POST}),
        "instagram.com": ("Instagram", {"/p/": ContentType.IMAGE, "/reel/": ContentType.VIDEO, "/tv/": ContentType.VIDEO}),
        "facebook.com": ("Facebook", {"/posts/": ContentType.SOCIAL_POST, "/videos/": ContentType.VIDEO}),
        "tiktok.com": ("TikTok", {"/@": ContentType.VIDEO, "/video/": ContentType.VIDEO}),
        "reddit.com": ("Reddit", {"/comments/": ContentType.SOCIAL_POST, "/r/": ContentType.SOCIAL_POST}),
        "news.ycombinator.com": ("Hacker News", {"": ContentType.SOCIAL_POST}),
    }

    TIMESTAMP_META_TAGS = ("article:published_time", "og:article:published_time", "pubdate", "dateModified", "datePublished")
    AUTHOR_META_TAGS = ("article:author", "og:author", "author")

    def _parse_url(self, url: str) -> ParseResult:
        """Parse and validate URL."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidURLError(f"Invalid URL format: {url}")
        return parsed

    def _identify_platform_and_type(self, parsed_url: ParseResult) -> tuple[str, ContentType]:
        """Identify platform and content type from parsed URL."""
        domain = parsed_url.netloc.lower().replace("www.", "")
        path = parsed_url.path.lower()

        for platform_domain, (platform_name, type_patterns) in self.PLATFORM_MAPPING.items():
            if domain == platform_domain or domain.endswith("." + platform_domain):
                for pattern, content_type in type_patterns.items():
                    if pattern == "" or pattern in path:
                        return platform_name, content_type
                return platform_name, ContentType.ARTICLE

        return domain.split(".")[0].capitalize(), ContentType.ARTICLE

    def _find_meta_tag(self, soup: BeautifulSoup, tag_name: str) -> Optional[Tag]:
        """Find a meta tag by property or name attribute."""
        meta = soup.find("meta", property=tag_name)
        if meta is None:
            meta = soup.find("meta", attrs={"name": tag_name})
        return meta

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string using dateutil."""
        return date_parser.parse(datetime_str)

    def _extract_from_soup(self, soup: BeautifulSoup) -> tuple[Optional[datetime], Optional[str], Optional[str]]:
        """Extract timestamp, author, and title from a single soup instance."""
        timestamp = None
        author = None
        title = None

        # Extract timestamp from <time> tags
        for time_tag in soup.find_all("time", attrs={"datetime": True}):
            datetime_str = time_tag.get("datetime")
            if datetime_str:
                try:
                    timestamp = self._parse_datetime(datetime_str)
                    break
                except (ValueError, TypeError):
                    continue

        # Extract timestamp from meta tags
        if timestamp is None:
            for meta_tag in self.TIMESTAMP_META_TAGS:
                meta = self._find_meta_tag(soup, meta_tag)
                if meta and meta.get("content"):
                    try:
                        timestamp = self._parse_datetime(meta["content"])
                        break
                    except (ValueError, TypeError):
                        continue

        # Extract author from meta tags
        for meta_tag in self.AUTHOR_META_TAGS:
            meta = self._find_meta_tag(soup, meta_tag)
            if meta and meta.get("content"):
                author = meta["content"].strip()
                break

        # Fallback to <author> or <byline> elements
        if author is None:
            author_tag = soup.find("author") or soup.find("byline")
            if author_tag:
                author = author_tag.get_text(strip=True)

        # Extract title: og:title > twitter:title > <title>
        og_title = self._find_meta_tag(soup, "og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        else:
            twitter_title = self._find_meta_tag(soup, "twitter:title")
            if twitter_title and twitter_title.get("content"):
                title = twitter_title["content"].strip()
            else:
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)

        return timestamp, author, title

    async def extract_metadata(self, url: str, html_content: Optional[str] = None) -> ContentMetadata:
        """
        Extracts metadata from a URL and optionally HTML content.

        Args:
            url: The source URL of the content.
            html_content: Optional HTML content for deeper metadata extraction.

        Returns:
            A ContentMetadata object with extracted metadata.

        Raises:
            InvalidURLError: If the URL is invalid.
        """
        if not url or not isinstance(url, str):
            raise InvalidURLError("URL must be a non-empty string.")

        url = url.strip()
        parsed_url = self._parse_url(url)
        platform, content_type = self._identify_platform_and_type(parsed_url)

        timestamp, author, title = None, None, None
        if html_content:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                timestamp, author, title = self._extract_from_soup(soup)
            except Exception:
                pass

        return ContentMetadata(
            platform=platform,
            content_type=content_type,
            url=url,
            timestamp=timestamp,
            author=author,
            title=title,
        )
