import logging
import uuid
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chunk import DocumentChunk
from backend.app.models.document import Document
from backend.app.models.metadata import DocumentMetadata
from processing.models.result import ProcessingResult
from processing.registry import ProcessorRegistry, get_default_registry
from storage.base import StorageProvider
from storage.local_storage import LocalStorageProvider

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Coordinates document processing pipeline:
    Document
    -> validation
    -> processor selection (via ProcessorRegistry)
    -> content extraction
    -> OCR if required
    -> normalized text
    -> processing result
    -> persistence of chunks, metadata, and status
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_provider: StorageProvider,
        registry: Optional[ProcessorRegistry] = None,
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.registry = registry or get_default_registry()

    async def process_file(
        self,
        file_path: Path,
        mime_type: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Processes a raw file directly using the registered processor.
        Returns the structured ProcessingResult without touching the database.
        """
        path = Path(file_path)
        processor = self.registry.get_processor(mime_type=mime_type, file_path=path)
        return await processor.process(path)

    async def process_document(
        self,
        document_id: uuid.UUID,
    ) -> ProcessingResult:
        """
        Full orchestration for an archival Document record:
        1. Resolves document and media asset
        2. Dispatches file to appropriate processor
        3. Obtains ProcessingResult
        4. Persists extracted text as DocumentChunk records linked to document_id
        5. Updates Document metadata with discovered file metadata
        6. Updates Document status to 'PROCESSED' and processing_stage to 'TEXT_EXTRACTED'
        """
        stmt = select(Document).where(Document.id == document_id)
        res = await self.session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        # Determine media path
        local_path: Optional[Path] = None
        mime_type: Optional[str] = None

        if doc.media_assets:
            asset = doc.media_assets[0]
            mime_type = asset.mime_type
            if isinstance(self.storage_provider, LocalStorageProvider):
                local_path = self.storage_provider.get_local_path(asset.storage_key)

        if not local_path or not local_path.exists():
            raise FileNotFoundError(
                f"No readable physical media asset found for document {document_id}."
            )

        # 1. Select processor & execute pure processing pipeline
        processor = self.registry.get_processor(mime_type=mime_type, file_path=local_path)
        logger.info(
            f"Processing document {document_id} ({local_path.name}) with {processor.processor_name}"
        )
        processing_result = await processor.process(local_path)

        # 2. Persist DocumentChunk records linked to document_id
        # Delete existing chunks if any (idempotency)
        existing_chunks_stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        existing_chunks = (await self.session.execute(existing_chunks_stmt)).scalars().all()
        for chunk in existing_chunks:
            await self.session.delete(chunk)

        chunk_index = 0
        for page in processing_result.pages:
            if page.text and page.text.strip():
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=page.text,
                    page_number=page.page_number,
                    token_count=page.word_count,
                )
                self.session.add(chunk)
                chunk_index += 1

        # If document had no page text, save single fallback chunk with full extracted text or summary
        if chunk_index == 0:
            fallback_text = (
                processing_result.extracted_text
                or f"Document: {doc.title}. {doc.description or ''}"
            ).strip()
            chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=0,
                content=fallback_text,
                page_number=1,
                token_count=len(fallback_text.split()),
            )
            self.session.add(chunk)

        # 3. Merge discovered file metadata into DocumentMetadata
        meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
        meta_res = await self.session.execute(meta_stmt)
        doc_meta = meta_res.scalar_one_or_none()

        if doc_meta:
            raw_meta = dict(doc_meta.raw_metadata or {})
            raw_meta["file_extracted_metadata"] = processing_result.metadata
            doc_meta.raw_metadata = raw_meta

            # Record provenance
            provenance = list(doc_meta.provenance or [])
            provenance.append({
                "step": "document_processing",
                "processor": processing_result.processor_name,
                "processor_version": processing_result.processor_version,
                "ocr_used": processing_result.ocr_used,
                "confidence": processing_result.confidence,
                "total_pages": processing_result.total_pages,
            })
            doc_meta.provenance = provenance

        # 4. Update Document status and stage
        doc.status = "PROCESSED"
        doc.processing_stage = "TEXT_EXTRACTED"

        await self.session.commit()
        logger.info(
            f"Successfully processed document {document_id}: persisted {max(chunk_index, 1)} chunks."
        )

        return processing_result
