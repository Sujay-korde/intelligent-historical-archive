import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from ingestion.adapters.base import SourceAdapter
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter
from ingestion.models.canonical import CanonicalArchiveRecord, SearchPage
from ingestion.services.ingestion_service import CoreIngestionService
from processing.jobs.base import JobManager
from storage.base import StorageProvider

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        storage_provider: StorageProvider,
        job_manager: Optional[JobManager] = None,
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.job_manager = job_manager
        self.core_service = CoreIngestionService(
            session=session,
            storage_provider=storage_provider,
            job_manager=job_manager,
        )

        # Registered adapters
        self._adapters: Dict[str, SourceAdapter] = {
            "library_of_congress": LibraryOfCongressAdapter(),
            "internet_archive": InternetArchiveAdapter(),
        }

    def get_adapter(self, source_name: str) -> SourceAdapter:
        if source_name not in self._adapters:
            raise ValueError(f"Unknown source adapter: {source_name}")
        return self._adapters[source_name]

    async def search_source(
        self, source_name: str, query: str, limit: int = 10, cursor: Optional[str] = None
    ) -> SearchPage:
        adapter = self.get_adapter(source_name)
        return await adapter.search(query=query, limit=limit, cursor=cursor)

    async def ingest_record(
        self, source_name: str, source_id: str, auto_process: bool = True
    ) -> Dict[str, Any]:
        adapter = self.get_adapter(source_name)
        document = await self.core_service.ingest_from_adapter(
            adapter=adapter,
            source_id=source_id,
            auto_process=auto_process,
        )
        await self.session.commit()

        return {
            "document_id": str(document.id),
            "source": document.source,
            "source_id": document.source_id,
            "title": document.title,
            "status": document.status,
            "processing_stage": document.processing_stage,
        }
