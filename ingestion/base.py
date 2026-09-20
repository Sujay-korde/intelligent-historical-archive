from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional
from backend.app.schemas.canonical import (
    CanonicalArchiveRecord,
    SearchPage,
    SourceRawRecord,
    SourceSearchResult,
)


class SourceAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for the source (e.g. 'library_of_congress', 'internet_archive')."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10, cursor: Optional[str] = None) -> SearchPage:
        """Search the external archive with cursor-based pagination."""
        pass

    @abstractmethod
    async def fetch_record(self, source_id: str) -> SourceRawRecord:
        """Fetch full raw metadata for a specific record."""
        pass

    @abstractmethod
    async def stream_media(self, media_url: str) -> AsyncIterator[bytes]:
        """Stream digital asset chunks directly without buffering full file into memory."""
        pass

    @abstractmethod
    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        """Transform raw source metadata into the canonical archive record."""
        pass
