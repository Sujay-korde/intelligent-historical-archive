import logging
import uuid
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import EmbeddingProvider, ExtractedEnrichment, LLMProvider
from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.repositories.chunk_repo import ChunkRepository
from backend.app.repositories.document_repo import DocumentRepository
from backend.app.repositories.entity_repo import EntityRepository
from processing.base import DocumentProcessor, ExtractedContent, ExtractedPage
from processing.chunking.base import Chunker
from processing.chunking.text_chunker import TextChunker
from processing.jobs.base import JobManager
from processing.processors.pdf_processor import PDFProcessor
from processing.processors.text_processor import TextProcessor
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
    ):
        self.session = session
        self.storage_provider = storage_provider
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.job_manager = job_manager
        self.chunker: Chunker = TextChunker()

        self.processors = [PDFProcessor(), TextProcessor()]

    def _select_processor(self, mime_type: str, file_name: str) -> DocumentProcessor:
        for p in self.processors:
            if p.can_process(mime_type, file_name):
                return p
        return self.processors[0]

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

            if not file_found:
                # Use document title, description, and subjects to construct synthetic content
                desc = doc.description or f"Archival document on {doc.title}"
                full_text = f"Title: {doc.title}\n\nDescription: {desc}\n\nSource: {doc.source}"
                extracted_content = ExtractedContent(
                    pages=[ExtractedPage(page_number=1, text=full_text)],
                    total_pages=1,
                    full_text=full_text,
                )

            # 3. AI Enrichment (Metadata & Entities)
            if job_id:
                await self.job_manager.update_progress(job_id, step="AI_ENRICHMENT", progress_pct=40)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="AI_ENRICHMENT")
            await self.session.commit()

            enrichment_prompt = f"Title: {doc.title}\nContent:\n{extracted_content.full_text[:4000]}"
            ai_resp = await self.llm_provider.extract_structured(
                prompt=enrichment_prompt,
                schema=ExtractedEnrichment,
                context={"text": extracted_content.full_text},
            )
            enrichment_data: ExtractedEnrichment = ai_resp.data

            # Update document metadata with AI insights
            if doc.doc_metadata:
                doc.doc_metadata.ai_metadata = {
                    "summary": enrichment_data.metadata.summary,
                    "historical_period": enrichment_data.metadata.historical_period,
                    "topics": enrichment_data.metadata.topics,
                    "geographic_references": enrichment_data.metadata.geographic_references,
                    "model": ai_resp.model_name,
                }
                # Append to provenance
                prov_list = list(doc.doc_metadata.provenance or [])
                prov_list.append({
                    "field": "ai_metadata",
                    "value": "enriched",
                    "source": "AI",
                    "confidence": enrichment_data.metadata.confidence,
                    "model_name": ai_resp.model_name,
                })
                doc.doc_metadata.provenance = prov_list

            # 4. Chunking
            if job_id:
                await self.job_manager.update_progress(job_id, step="CHUNKING", progress_pct=65)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="CHUNKING")
            await self.session.commit()

            chunks = self.chunker.chunk(
                extracted_content,
                max_tokens=settings.MAX_CHUNK_TOKENS,
                overlap=settings.CHUNK_OVERLAP_TOKENS,
            )

            # 5. Embeddings
            if job_id:
                await self.job_manager.update_progress(job_id, step="GENERATING_EMBEDDINGS", progress_pct=80)
            await doc_repo.update_status(document_id, status="PROCESSING", processing_stage="EMBEDDING")
            await self.session.commit()

            chunk_texts = [c.content for c in chunks]
            embeddings = await self.embedding_provider.embed_texts(chunk_texts)

            # 6. Save Chunks & Embeddings in PostgreSQL
            await chunk_repo.save_chunks_and_embeddings(
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
                model_name=self.embedding_provider.model_name,
                model_version=self.embedding_provider.model_version,
                dimension=self.embedding_provider.dimension,
            )

            # 7. Persist Entities & Relationships
            saved_entities = []
            for ent_dto in enrichment_data.entities:
                ent_model = await entity_repo.upsert_entity(
                    name=ent_dto.name,
                    entity_type=ent_dto.entity_type,
                    authority_uri=ent_dto.authority_uri,
                    description=ent_dto.description,
                )
                await entity_repo.link_document_entity(
                    document_id=document_id,
                    entity_id=ent_model.id,
                    confidence=ent_dto.confidence,
                    provenance="AI",
                    relationship_type="MENTIONS",
                )
                saved_entities.append(ent_model)

            # Create cross-entity relationships between co-occurring entities
            for i in range(len(saved_entities)):
                for j in range(i + 1, len(saved_entities)):
                    e1, e2 = saved_entities[i], saved_entities[j]
                    rel_type = "RELATED_TO"
                    if e1.entity_type == "PERSON" and e2.entity_type == "ORGANIZATION":
                        rel_type = "AFFILIATED_WITH"
                    elif e1.entity_type == "ORGANIZATION" and e2.entity_type == "LOCATION":
                        rel_type = "LOCATED_IN"

                    await entity_repo.create_relationship(
                        source_entity_id=e1.id,
                        target_entity_id=e2.id,
                        relationship_type=rel_type,
                        confidence=0.85,
                        source_document_id=document_id,
                    )

            # 8. Calculate Quality Score
            quality = 85.0
            if doc.doc_metadata and doc.doc_metadata.creators:
                quality += 5.0
            if doc.doc_metadata and doc.doc_metadata.date_raw:
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
