import logging
import uuid
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import EmbeddingProvider, ExtractedEnrichment, LLMProvider
from ai.services.enrichment_service import EnrichmentService
from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.repositories.chunk_repo import ChunkRepository
from backend.app.repositories.document_repo import DocumentRepository
from backend.app.repositories.entity_repo import EntityRepository
from processing.base import BaseProcessor, DocumentProcessor, ExtractedContent, ExtractedPage
from processing.chunking.base import BaseChunker, Chunker
from processing.chunking.text_chunker import TextChunker
from processing.jobs.base import JobManager
from processing.registry import ProcessorRegistry, get_default_registry
from processing.services.embedding_pipeline_service import EmbeddingPipelineService
from storage.base import StorageProvider
from storage.local_storage import LocalStorageProvider

logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        storage_provider: StorageProvider,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        job_manager: JobManager,
        chunker: Optional[BaseChunker] = None,
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.job_manager = job_manager
        self.chunker: BaseChunker = chunker or TextChunker()
        self.registry: ProcessorRegistry = get_default_registry()
        self.enrichment_service = EnrichmentService(provider=self.llm_provider)
        self.embedding_pipeline = EmbeddingPipelineService(
            session=self.session,
            embedding_provider=self.embedding_provider,
            chunker=self.chunker,
        )

    def _select_processor(self, mime_type: str, file_name: str) -> BaseProcessor:
        try:
            return self.registry.get_processor(mime_type=mime_type, file_path=file_name)
        except Exception:
            return self.registry.get_processor(extension="pdf")

    async def process_document(
        self, document_id: uuid.UUID, job_id: Optional[str] = None
    ) -> None:
        doc_repo = DocumentRepository(self.session)
        chunk_repo = ChunkRepository(self.session)
        entity_repo = EntityRepository(self.session)

        try:
            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                raise ValueError(f"Document not found: {document_id}")

            has_creators = bool(doc.doc_metadata and doc.doc_metadata.creators)
            has_date = bool(doc.doc_metadata and doc.doc_metadata.date_raw)
            doc_title = doc.title
            doc_desc = doc.description
            doc_source = doc.source

            # 1. Update status to PROCESSING
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="EXTRACTING_TEXT")
            if job_id:
                await self.job_manager.update_progress(job_id, step="EXTRACTING_TEXT", progress_pct=15)
            await self.session.commit()

            # 2. Extract content from media asset or fallback to metadata text
            extracted_content: ExtractedContent
            file_found = False

            if doc.media_assets:
                asset = doc.media_assets[0]
                if isinstance(self.storage_provider, LocalStorageProvider):
                    local_path = self.storage_provider.get_local_path(asset.storage_key)
                    if local_path.exists():
                        processor = self._select_processor(asset.mime_type, local_path.name)
                        extracted_content = await processor.extract_content(local_path)
                        file_found = True

            if not file_found or not extracted_content or not (extracted_content.full_text or "").strip():
                # Use document title, description, and metadata to construct rich contextual content
                desc = doc.description or f"Archival document on {doc.title}"
                creator_str = ""
                if doc.doc_metadata and doc.doc_metadata.creators:
                    creator_str = ", ".join([c.get("name", "") for c in doc.doc_metadata.creators if isinstance(c, dict) and c.get("name")])
                date_str = doc.doc_metadata.date_raw if (doc.doc_metadata and doc.doc_metadata.date_raw) else ""
                subj_str = ", ".join(doc.doc_metadata.subjects) if (doc.doc_metadata and doc.doc_metadata.subjects) else ""
                full_text = f"Title: {doc.title}\nCreator: {creator_str}\nDate: {date_str}\nSubjects: {subj_str}\nDescription: {desc}\nArchival Format: {doc.record_type}\nSource: {doc.source} ({doc.source_id})"
                extracted_content = ExtractedContent(
                    pages=[ExtractedPage(page_number=1, text=full_text)],
                    total_pages=1,
                    full_text=full_text,
                )

            # 3. AI Enrichment (Metadata, Entities, Summaries)
            if job_id:
                await self.job_manager.update_progress(job_id, step="AI_ENRICHMENT", progress_pct=40)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="AI_ENRICHMENT")
            await self.session.commit()

            ai_resp = await self.enrichment_service.enrich_and_persist(
                session=self.session,
                document_id=document_id,
                text=extracted_content.full_text,
                context={"title": doc.title},
            )
            enrichment_data = ai_resp.data

            # 4. Chunking
            if job_id:
                await self.job_manager.update_progress(job_id, step="CHUNKING", progress_pct=65)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="CHUNKING")
            await self.session.commit()

            chunks = self.embedding_pipeline.create_chunks(
                extracted_content,
                max_tokens=settings.MAX_CHUNK_TOKENS,
                overlap=settings.CHUNK_OVERLAP_TOKENS,
            )

            # 5. Embeddings
            if job_id:
                await self.job_manager.update_progress(job_id, step="GENERATING_EMBEDDINGS", progress_pct=80)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="EMBEDDING")
            await self.session.commit()

            embeddings = await self.embedding_pipeline.generate_embeddings(chunks)

            # 6. Save Chunks & Embeddings in pgvector
            embedded_chunks = await self.embedding_pipeline.store_in_pgvector(
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            # 7. Entities & Relationships (Persisted during Enrichment step)
            saved_entities = enrichment_data.entities

            # 8. Calculate Quality Score
            quality = 85.0
            if has_creators:
                quality += 5.0
            if has_date:
                quality += 5.0
            if len(saved_entities) >= 3:
                quality += 5.0

            # 9. Mark Document READY & INDEXED
            await doc_repo.update_status(
                document_id,
                status="READY",
                processing_stage="INDEXED",
                quality_score=min(100.0, quality),
            )

            if job_id:
                await self.job_manager.complete_job(
                    job_id,
                    result={
                        "chunks_count": len(chunks),
                        "entities_count": len(saved_entities),
                        "quality_score": quality,
                    },
                )

            await self.session.commit()
            logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks and {len(saved_entities)} entities.")

        except Exception as e:
            logger.exception(f"Error processing document {document_id}: {e}")
            await self.session.rollback()
            await doc_repo.update_status(document_id, status="FAILED", processing_stage="ERROR")
            if job_id:
                await self.job_manager.fail_job(job_id, error_message=str(e))
            await self.session.commit()
            raise
