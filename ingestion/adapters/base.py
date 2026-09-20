from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from ingestion.models.canonical import (
    CanonicalArchiveRecord,
    SearchPage,
    SourceRawRecord,
)


class SourceAdapter(ABC):
    """
    Common contract for external archive repository adapters.
    Conceptually supports search, fetch_record, download_media (or stream_media), and normalize.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for the source (e.g., 'library_of_congress', 'internet_archive')."""
        pass

    @property
    def adapter_version(self) -> str:
        """Version string for the adapter implementation."""
        return "1.0.0"

    @abstractmethod
    async def search(
        self, query: str, limit: int = 10, cursor: Optional[str] = None
    ) -> SearchPage:
        """Search the external archive with cursor or page-based pagination."""
        pass

    @abstractmethod
    async def fetch_record(self, source_id: str) -> SourceRawRecord:
        """Fetch full raw metadata payload for a specific record."""
        pass

    @abstractmethod
    async def download_media(self, media_url: str) -> AsyncIterator[bytes]:
        """Stream/download digital asset chunks directly without buffering full file into memory."""
        pass

    async def stream_media(self, media_url: str) -> AsyncIterator[bytes]:
        """Alias for download_media for streaming IO compatibility."""
        return await self.download_media(media_url)

    @abstractmethod
    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        """Transform raw source metadata into the standard CanonicalArchiveRecord structure."""
        pass
