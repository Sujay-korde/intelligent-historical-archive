from ingestion.adapters.base import SourceAdapter
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter

__all__ = [
    "SourceAdapter",
    "LibraryOfCongressAdapter",
    "InternetArchiveAdapter",
]
