from typing import Any, Dict, Optional


class ArchiveException(Exception):
    """Base exception for all archive domain errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SourceAdapterError(ArchiveException):
    """Base error for external archive source adapters."""
    pass


class SourceUnavailableError(SourceAdapterError):
    """Raised when an external archive repository (LOC, Internet Archive, etc.) is unreachable."""
    pass


class SourceAPIError(SourceAdapterError):
    """Raised when an external archive API returns an HTTP or payload error."""
    pass


class SourceRateLimitError(SourceAdapterError):
    """Raised when an external source throttles requests."""
    pass


class SourceRecordNotFoundError(SourceAdapterError):
    """Raised when a specific source record is not found in the external repository."""
    pass


class SourceMediaDownloadError(SourceAdapterError):
    """Raised when streaming or downloading digital assets fails."""
    pass


class DocumentProcessingError(ArchiveException):
    """Raised during document content extraction, parsing, or OCR."""
    pass


class StorageError(ArchiveException):
    """Raised when object/file storage operations fail."""
    pass


class AIProviderError(ArchiveException):
    """Raised when LLM or embedding calls fail."""
    pass


class JobError(ArchiveException):
    """Raised during job queueing or execution."""
    pass
