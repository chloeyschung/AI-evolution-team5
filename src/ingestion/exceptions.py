class ExtractionError(Exception):
    """Raised when content extraction fails."""

    pass


class ShareError(Exception):
    """Base exception for share sheet processing failures."""

    pass


class InvalidShareDataError(ShareError):
    """Raised when share data is malformed or missing required fields."""

    pass


class UnsupportedShareTypeError(ShareError):
    """Raised when the share data type cannot be processed."""

    pass


class ImageProcessingError(ShareError):
    """Raised when image data processing fails."""

    pass


class DeepLinkValidationError(ShareError):
    """Raised when a deep link cannot be parsed or validated."""

    pass
