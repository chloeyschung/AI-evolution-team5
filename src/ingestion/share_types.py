"""Data types for mobile share sheet integration."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ShareDataType(Enum):
    """Types of data that can be shared via mobile share sheet."""

    URL = "url"
    PLAIN_TEXT = "plain_text"
    DEEP_LINK = "deep_link"
    IMAGE = "image"


@dataclass
class ShareData:
    """Structured representation of mobile share sheet data."""

    data_type: ShareDataType
    content: str
    metadata: Optional[dict] = None
    source_platform: Optional[str] = None
