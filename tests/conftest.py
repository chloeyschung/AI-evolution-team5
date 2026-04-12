"""Shared pytest fixtures for ingestion module tests."""

import pytest
from unittest.mock import AsyncMock

from src.ai.metadata_extractor import ContentMetadata, ContentType
from src.ingestion.extractor import ContentExtractor
from src.ai.metadata_extractor import MetadataExtractor


@pytest.fixture
def content_extractor_mock():
    """Create mocked ContentExtractor."""
    mock = AsyncMock(spec=ContentExtractor)
    mock.extract_text = AsyncMock(return_value="Extracted content")
    return mock


@pytest.fixture
def metadata_extractor_mock():
    """Create mocked MetadataExtractor."""
    mock = AsyncMock(spec=MetadataExtractor)
    mock.extract_metadata = AsyncMock(
        return_value=ContentMetadata(
            platform="Test",
            content_type=ContentType.ARTICLE,
            url="https://example.com",
        )
    )
    return mock


@pytest.fixture
def metadata_extractor_mock_testplatform():
    """Create mocked MetadataExtractor with TestPlatform."""
    mock = AsyncMock(spec=MetadataExtractor)
    mock.extract_metadata = AsyncMock(
        return_value=ContentMetadata(
            platform="TestPlatform",
            content_type=ContentType.ARTICLE,
            url="https://example.com",
        )
    )
    return mock
