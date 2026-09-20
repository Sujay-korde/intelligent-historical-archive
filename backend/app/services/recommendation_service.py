import logging
import uuid
from typing import Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.repositories.chunk_repo import ChunkRepository
from backend.app.schemas.recommendation import (
    RecommendationResponse,
    RecommendedDocumentItem,
)
from backend.app.schemas.search import DocumentSummary, PreviewInformation

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Recommendation service for discovering related archival documents.
    Combines:
    1. Semantic vector similarity (embeddings)
    2. Shared knowledge entities (people, locations, organizations)
    3. Archival metadata overlap (subjects, historical periods, creators)

    As defined in PRD.md Section 26:
    Related Document Score = 0.6 * SemanticSimilarity + 0.2 * EntityOverlap + 0.2 * MetadataOverlap
    """

    def __init__(self, session: AsyncSession, chunk_repo: Optional[ChunkRepository] = None):
        self.session = session
        self.chunk_repo = chunk_repo or ChunkRepository(session)

    async def get_recommendations(
        self, document_id: uuid.UUID, limit: int = 5
    ) -> RecommendationResponse:
        # 1. Retrieve target document with full associations
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.doc_metadata),
                selectinload(Document.entities).selectinload(DocumentEntity.entity),
                selectinload(Document.chunks).selectinload(DocumentChunk.embeddings),
                selectinload(Document.media_assets),
            )
        )
        target_doc = (await self.session.execute(stmt)).scalar_one_or_none()
        if not target_doc:
            raise ValueError(f"Target document not found: {document_id}")

        # 2. Extract target vector representation
        target_vector: Optional[List[float]] = None
        for chunk in target_doc.chunks:
            for emb in chunk.embeddings:
                if emb.is_active and emb.embedding is not None:
                    target_vector = list(emb.embedding) if hasattr(emb.embedding, "__iter__") else []
                    break
            if target_vector:
                break

        # Extract target entities and metadata terms
        target_entities: Set[str] = {
            de.entity.name.lower() for de in target_doc.entities if de.entity
        }
        target_meta = target_doc.doc_metadata
        target_subjects: Set[str] = (
            {str(s).lower() for s in target_meta.subjects} if target_meta and target_meta.subjects else set()
        )
        target_period: Optional[str] = (
            target_meta.ai_metadata.get("historical_period")
            if target_meta and target_meta.ai_metadata
            else None
        )

        # 3. Retrieve semantic candidate matches using chunk repository
        semantic_matches: Dict[uuid.UUID, float] = {}
        if target_vector:
            raw_matches = await self.chunk_repo.vector_similarity_search(
                query_vector=target_vector,
                limit=limit * 4,
            )
            for m in raw_matches:
                d_id = m["document_id"]
                if d_id != document_id:
                    sim = m["similarity"]
                    if d_id not in semantic_matches or sim > semantic_matches[d_id]:
                        semantic_matches[d_id] = sim

        # 4. Fetch candidate documents for hydration and overlap scoring
        candidate_ids = set(semantic_matches.keys())

        # If semantic matches are fewer than requested limit, pull additional documents for metadata/entity comparison
        if len(candidate_ids) < limit * 2:
            alt_stmt = (
                select(Document.id)
                .where(Document.id != document_id)
                .limit(limit * 3)
            )
            alt_ids = (await self.session.execute(alt_stmt)).scalars().all()
            candidate_ids.update(alt_ids)

        if not candidate_ids:
            return RecommendationResponse(
                source_document_id=document_id,
                total_recommendations=0,
                recommendations=[],
            )

        cand_stmt = (
            select(Document)
            .where(Document.id.in_(list(candidate_ids)))
            .options(
                selectinload(Document.doc_metadata),
                selectinload(Document.entities).selectinload(DocumentEntity.entity),
                selectinload(Document.media_assets),
            )
        )
        candidates = (await self.session.execute(cand_stmt)).scalars().all()

        scored_recommendations: List[RecommendedDocumentItem] = []

        for cand in candidates:
            # A. Semantic Score (0.0 to 1.0)
            sem_sim = semantic_matches.get(cand.id, 0.0)

            # B. Entity Overlap Score (Jaccard / intersection)
            cand_entities: Set[str] = {
                de.entity.name.lower() for de in cand.entities if de.entity
            }
            shared_ents = [
                de.entity.name for de in cand.entities if de.entity and de.entity.name.lower() in target_entities
            ]
            union_ents = target_entities | cand_entities
            entity_score = (len(shared_ents) / len(union_ents)) if union_ents else 0.0

            # C. Metadata Overlap Score
            cand_meta = cand.doc_metadata
            cand_subjects: Set[str] = (
                {str(s).lower() for s in cand_meta.subjects} if cand_meta and cand_meta.subjects else set()
            )
            shared_subjs = [
                s for s in (cand_meta.subjects if cand_meta else []) if str(s).lower() in target_subjects
            ]
            union_subjs = target_subjects | cand_subjects
            subj_score = (len(shared_subjs) / len(union_subjs)) if union_subjs else 0.0

            # Period match
            cand_period = (
                cand_meta.ai_metadata.get("historical_period")
                if cand_meta and cand_meta.ai_metadata
                else None
            )
            period_match = bool(
                target_period and cand_period and target_period.lower() == cand_period.lower()
            )
            period_score = 1.0 if period_match else 0.0

            meta_score = (subj_score * 0.7) + (period_score * 0.3)

            # D. Composite Weighted Recommendation Score
            composite_score = (0.6 * sem_sim) + (0.2 * entity_score) + (0.2 * meta_score)

            # E. Rationale / Explanation
            reasons = []
            if sem_sim > 0.4:
                reasons.append(f"Semantic similarity ({sem_sim:.2f})")
            if shared_ents:
                reasons.append(f"Shared entities: {', '.join(shared_ents[:3])}")
            if shared_subjs:
                reasons.append(f"Shared subjects: {', '.join(shared_subjs[:2])}")
            if period_match:
                reasons.append(f"Same era: {target_period}")

            explanation = " + ".join(reasons) if reasons else "Related archival collection"

            # Preview information
            preview = PreviewInformation()
            if cand.media_assets:
                primary = next(
                    (a for a in cand.media_assets if a.asset_role == "primary"),
                    cand.media_assets[0],
                )
                preview = PreviewInformation(
                    has_media=True,
                    media_type=primary.media_type,
                    mime_type=primary.mime_type,
                    storage_key=primary.storage_key,
                    access_url=cand.source_url,
                    file_size_bytes=primary.file_size_bytes,
                )

            doc_summary = DocumentSummary(
                id=cand.id,
                title=cand.title,
                description=cand.description,
                source=cand.source,
                source_id=cand.source_id,
                record_type=cand.record_type,
                source_url=cand.source_url,
                status=cand.status,
            )

            scored_recommendations.append(
                RecommendedDocumentItem(
                    document=doc_summary,
                    score=round(composite_score, 4),
                    semantic_similarity=round(sem_sim, 4),
                    shared_entities=shared_ents,
                    shared_subjects=shared_subjs,
                    shared_historical_period=cand_period if period_match else None,
                    explanation=explanation,
                    preview=preview,
                )
            )

        scored_recommendations.sort(key=lambda x: x.score, reverse=True)
        final_list = scored_recommendations[:limit]

        return RecommendationResponse(
            source_document_id=document_id,
            total_recommendations=len(final_list),
            recommendations=final_list,
        )
