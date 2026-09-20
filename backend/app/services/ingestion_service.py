import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.repositories.document_repo import DocumentRepository
from backend.app.schemas.canonical import CanonicalArchiveRecord, SearchPage
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter
from ingestion.adapters.upload_adapter import LocalUploadAdapter
from ingestion.base import SourceAdapter
from processing.jobs.base import JobManager
from storage.base import StorageProvider

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        storage_provider: StorageProvider,
        job_manager: JobManager,
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.job_manager = job_manager

        # Registered adapters
        self._adapters: Dict[str, SourceAdapter] = {
            "library_of_congress": LibraryOfCongressAdapter(),
            "internet_archive": InternetArchiveAdapter(),
            "upload": LocalUploadAdapter(),
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
        doc_repo = DocumentRepository(self.session)

        # 1. Fetch raw record
        raw_record = await adapter.fetch_record(source_id)

        # 2. Normalize to CanonicalArchiveRecord
        canonical_record = adapter.normalize(raw_record)

        # 3. Stream and store primary media asset if URL available
        if canonical_record.media_assets and canonical_record.media_assets[0].url:
            primary_asset = canonical_record.media_assets[0]
            ext = "pdf" if "pdf" in primary_asset.mime_type else "jpg"
            storage_key = f"{source_name}/{source_id}/{primary_asset.asset_id}.{ext}"

            try:
                media_stream = await adapter.stream_media(primary_asset.url)
                stored_meta = await self.storage_provider.save_stream(
                    stream=media_stream,
                    destination_key=storage_key,
                    content_type=primary_asset.mime_type,
                )
                primary_asset.storage_key = stored_meta.storage_key
                primary_asset.file_size_bytes = stored_meta.file_size_bytes
                primary_asset.checksum_sha256 = stored_meta.checksum_sha256
            except Exception as e:
                logger.warning(f"Media streaming failed for {source_id}: {e}")

        # 4. Persist Document & Metadata in PostgreSQL
        document = await doc_repo.create_from_canonical(canonical_record)
        await self.session.commit()

        # 5. Enqueue processing job if requested
        job_ticket = None
        if auto_process:
            job_ticket = await self.job_manager.enqueue(
                document_id=str(document.id),
                job_type="PROCESS_DOCUMENT",
                payload={"document_id": str(document.id), "source": source_name},
            )

        return {
            "document_id": str(document.id),
            "source": document.source,
            "source_id": document.source_id,
            "title": document.title,
            "status": document.status,
            "job_id": job_ticket.job_id if job_ticket else None,
        }
