class SummarizationError(Exception):
    """Base exception for summarization failures."""
    pass

class APIConnectionError(SummarizationError):
    """Raised when the connection to the AI API fails."""
    pass

class ContentProcessingError(SummarizationError):
    """Raised when the input content cannot be processed."""
    pass

class InvalidResponseError(SummarizationError):
    """Raised when the AI returns an invalid or improperly formatted response."""
    pass


class MetadataExtractionError(Exception):
    """Base exception for metadata extraction failures."""
    pass

class InvalidURLError(MetadataExtractionError):
    """Raised when the URL is invalid or cannot be parsed."""
    pass

class UnsupportedPlatformError(MetadataExtractionError):
    """Raised when the platform cannot be identified."""
    pass