from abc import ABC, abstractmethod
from ingestion.models.canonical import CanonicalArchiveRecord, SourceRawRecord


class RecordNormalizer(ABC):
    """Abstract base class for source-specific record normalizers."""

    @abstractmethod
    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        """Transform raw source metadata into a normalized CanonicalArchiveRecord."""
        pass
