import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.repositories.document_repo import DocumentRepository
from ingestion.adapters.base import SourceAdapter
from ingestion.models.canonical import CanonicalArchiveRecord, SearchPage
from processing.jobs.base import JobManager
from storage.base import StorageProvider

logger = logging.getLogger(__name__)


class CoreIngestionService:
    """
    Source-Agnostic Core Ingestion Service.
    Operates strictly on CanonicalArchiveRecord and the common SourceAdapter interface.
    The core pipeline has no specialized logic for specific external archives.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_provider: StorageProvider,
        job_manager: Optional[JobManager] = None,
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.job_manager = job_manager
        self.doc_repo = DocumentRepository(session)

    async def ingest_from_adapter(
        self,
        adapter: SourceAdapter,
        source_id: str,
        auto_process: bool = True,
    ) -> Document:
        """
        Ingestion flow:
        source -> adapter -> canonical record -> database
        """
        # 1. Fetch raw source payload
        raw_record = await adapter.fetch_record(source_id)

        # 2. Normalize to CanonicalArchiveRecord
        canonical_record = adapter.normalize(raw_record)

        # 3. Stream & store media assets if available
        if canonical_record.media_assets and canonical_record.media_assets[0].url:
            primary_asset = canonical_record.media_assets[0]
            mime = (primary_asset.mime_type or "").lower()
            url_str = (primary_asset.url or "").lower()
            if "pdf" in mime or url_str.endswith(".pdf"):
                ext = "pdf"
            elif "audio" in mime or any(url_str.endswith(e) for e in [".mp3", ".m4a", ".wav", ".ogg"]):
                ext = "mp3" if "mpeg" in mime or url_str.endswith(".mp3") else "m4a"
            elif "video" in mime or any(url_str.endswith(e) for e in [".mp4", ".webm", ".mov", ".mkv"]):
                ext = "mp4"
            elif "png" in mime or url_str.endswith(".png"):
                ext = "png"
            elif any(url_str.endswith(e) for e in [".tif", ".tiff"]):
                ext = "tif"
            else:
                ext = "jpg"

            category = "documents"
            if "audio" in mime or ext in ["mp3", "m4a", "wav"]:
                category = "audio"
            elif "video" in mime or ext in ["mp4", "webm"]:
                category = "video"
            elif "image" in mime or ext in ["jpg", "jpeg", "png", "tif"]:
                category = "images"
            elif canonical_record.record_type == "manuscript":
                category = "manuscripts"

            storage_key = f"{category}/{canonical_record.source}/{canonical_record.source_id}.{ext}"

            if primary_asset.media_type == "video" and (primary_asset.file_size_bytes or 0) > 15_000_000:
                # For large motion picture video assets, stream directly from external repository
                primary_asset.storage_key = primary_asset.url
            else:
                try:
                    media_stream = await adapter.download_media(primary_asset.url)
                    stored_meta = await self.storage_provider.save_stream(
                        stream=media_stream,
                        destination_key=storage_key,
                        content_type=primary_asset.mime_type,
                    )
                    primary_asset.storage_key = stored_meta.storage_key
                    primary_asset.file_size_bytes = stored_meta.file_size_bytes
                    primary_asset.checksum_sha256 = stored_meta.checksum_sha256
                except Exception as e:
                    logger.warning(f"Media streaming/download failed for {canonical_record.source_id}: {e}")
                    primary_asset.storage_key = primary_asset.url

        # 4. Ingest canonical record into database
        return await self.ingest_canonical_record(canonical_record, auto_process=auto_process)

    async def ingest_canonical_record(
        self,
        canonical_record: CanonicalArchiveRecord,
        auto_process: bool = True,
    ) -> Document:
        """
        Persists a CanonicalArchiveRecord into PostgreSQL database.
        Creates Document, DocumentMetadata, and DocumentMediaAsset entries.
        """
        document = await self.doc_repo.create_from_canonical(canonical_record)
        await self.session.flush()

        # Enqueue processing job if job manager is provided
        if auto_process and self.job_manager:
            try:
                await self.job_manager.enqueue(
                    document_id=str(document.id),
                    job_type="PROCESS_DOCUMENT",
                    payload={"document_id": str(document.id), "source": canonical_record.source},
                )
            except Exception as e:
                logger.warning(f"Could not enqueue processing job for document {document.id}: {e}")

        return document
