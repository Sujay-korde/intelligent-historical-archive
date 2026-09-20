import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.factory import create_enrichment_provider
from ai.interfaces.extractor import AIEnrichmentProvider
from ai.models.enrichment import (
    AIEnrichmentResult,
    AIEntity,
    AIMetadata,
    AIResponseEnvelope,
    AISummary,
    EntityType,
)
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.metadata import DocumentMetadata
from backend.app.models.relationship import Relationship
from backend.app.repositories.entity_repo import EntityRepository

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Business logic service for document AI enrichment.
    Depends solely on abstract provider interfaces (AIEnrichmentProvider),
    never on vendor-specific LLM implementations.
    Enforces:
    1. Structured output extraction (Metadata, Entities, Summaries)
    2. Strict provenance retention (provider, model, version, confidence, timestamp)
    3. Source metadata preservation (raw_metadata and source fields remain untouched)
    4. Resilient failure isolation (document remains valid if AI call fails)
    """

    def __init__(
        self,
        provider: Optional[AIEnrichmentProvider] = None,
    ):
        self.provider = provider or create_enrichment_provider()

    async def enrich_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIResponseEnvelope[AIEnrichmentResult]:
        """
        Executes AI enrichment on arbitrary text with resilient fallback.
        """
        try:
            return await self.provider.enrich(text, context)
        except Exception as e:
            logger.error(f"AI enrichment failed: {e}. Generating graceful fallback.", exc_info=True)
            fallback_meta = AIMetadata(
                title=context.get("title") if context else None,
                language="English",
                confidence=0.5,
            )
            fallback_summary = AISummary(
                summary="Summary unavailable due to an AI processing exception.",
                confidence=0.0,
            )
            fallback_result = AIEnrichmentResult(
                metadata=fallback_meta,
                entities=[],
                summary=fallback_summary,
            )
            return AIResponseEnvelope(
                data=fallback_result,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                confidence=0.0,
                provenance="AI",
            )

    async def enrich_and_persist(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIResponseEnvelope[AIEnrichmentResult]:
        """
        Enriches document text and persists AI metadata and entities into the database:
        - Writes AI metadata strictly into doc_metadata.ai_metadata (source metadata untouched)
        - Appends AI provenance record into doc_metadata.provenance
        - Upserts extracted entities into entities and links them via document_entities
        - Creates cross-entity graph relationships
        """
        enrich_result = await self.enrich_text(text, context)
        ai_data = enrich_result.data

        # 1. Fetch document metadata
        meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
        meta_res = await session.execute(meta_stmt)
        doc_meta = meta_res.scalar_one_or_none()

        if doc_meta:
            # Store AI-enriched metadata SEPARATELY without overwriting original source metadata
            doc_meta.ai_metadata = {
                "title": ai_data.metadata.title,
                "creator": ai_data.metadata.creator,
                "date": ai_data.metadata.date,
                "location": ai_data.metadata.location,
                "organization": ai_data.metadata.organization,
                "document_type": ai_data.metadata.document_type,
                "language": ai_data.metadata.language,
                "subjects": ai_data.metadata.subjects,
                "topics": ai_data.metadata.topics,
                "historical_period": ai_data.metadata.historical_period,
                "summary": ai_data.summary.summary if ai_data.summary else None,
                "key_points": ai_data.summary.key_points if ai_data.summary else [],
                "confidence": enrich_result.confidence,
                "provider": enrich_result.provider,
                "model": enrich_result.model,
                "model_version": enrich_result.model_version,
                "timestamp": enrich_result.timestamp.isoformat(),
            }

            # Append audit trail to provenance
            provenance_list = list(doc_meta.provenance or [])
            provenance_list.append({
                "step": "ai_enrichment",
                "provider": enrich_result.provider,
                "model": enrich_result.model,
                "model_version": enrich_result.model_version,
                "confidence": enrich_result.confidence,
                "timestamp": enrich_result.timestamp.isoformat(),
                "provenance": "AI",
                "entities_count": len(ai_data.entities),
            })
            doc_meta.provenance = provenance_list

        # 2. Persist entities and document linkages
        entity_repo = EntityRepository(session)
        saved_entities = []

        for entity_dto in ai_data.entities:
            entity_model = await entity_repo.upsert_entity(
                name=entity_dto.name,
                entity_type=entity_dto.entity_type.value,
                authority_uri=entity_dto.authority_uri,
                description=entity_dto.description,
            )
            await entity_repo.link_document_entity(
                document_id=document_id,
                entity_id=entity_model.id,
                confidence=entity_dto.confidence,
                provenance="AI",
                relationship_type="MENTIONS",
            )
            saved_entities.append(entity_model)

        # 3. Create cross-entity co-occurrence relationships
        for i in range(len(saved_entities)):
            for j in range(i + 1, len(saved_entities)):
                e1, e2 = saved_entities[i], saved_entities[j]
                rel_type = "RELATED_TO"
                if e1.entity_type == "PERSON" and e2.entity_type == "ORGANIZATION":
                    rel_type = "AFFILIATED_WITH"
                elif e1.entity_type == "ORGANIZATION" and e2.entity_type == "LOCATION":
                    rel_type = "LOCATED_IN"
                elif e1.entity_type == "EVENT" and e2.entity_type == "LOCATION":
                    rel_type = "OCCURRED_IN"

                await entity_repo.create_relationship(
                    source_entity_id=e1.id,
                    target_entity_id=e2.id,
                    relationship_type=rel_type,
                    confidence=0.85,
                    source_document_id=document_id,
                )

        logger.info(
            f"Enriched document {document_id}: persisted {len(saved_entities)} entities with provenance."
        )
        return enrich_result
