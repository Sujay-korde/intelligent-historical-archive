import math
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.schemas.search import (
    DocumentSummary,
    MatchedEntityItem,
    PreviewInformation,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from backend.app.search.ranking.base import BaseRanker, CandidateMatch
from backend.app.search.ranking.rrf_ranker import ReciprocalRankFusionRanker


class SearchRepository:
    """
    Unified search repository providing:
    1. Dense semantic vector retrieval (pgvector)
    2. Sparse keyword / full-text retrieval
    3. Archival metadata filtering
    4. Modular rank fusion (RRF)
    5. Rich document result hydration
    """

    def __init__(self, session: AsyncSession, ranker: Optional[BaseRanker] = None):
        self.session = session
        self.ranker = ranker or ReciprocalRankFusionRanker(k=60)

    def _extract_snippet(self, content: str, query: str, max_chars: int = 240) -> str:
        """Extract a highlighted excerpt centered around matching query terms."""
        content_clean = re.sub(r"\s+", " ", content.strip())
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        if not query_words:
            return content_clean[:max_chars] + "..." if len(content_clean) > max_chars else content_clean

        lower_content = content_clean.lower()
        first_pos = -1
        for qw in query_words:
            pos = lower_content.find(qw)
            if pos != -1 and (first_pos == -1 or pos < first_pos):
                first_pos = pos

        if first_pos == -1:
            return content_clean[:max_chars] + "..." if len(content_clean) > max_chars else content_clean

        start = max(0, first_pos - 60)
        end = min(len(content_clean), start + max_chars)
        snippet = content_clean[start:end].strip()
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content_clean) else ""
        return f"{prefix}{snippet}{suffix}"

    def _build_metadata_filters(self, request: SearchRequest, stmt, has_doc_joined: bool = True):
        """Applies SQL-level metadata filters."""
        if request.source:
            stmt = stmt.where(Document.source == request.source)
        if request.record_type:
            stmt = stmt.where(Document.record_type == request.record_type)
        return stmt

    async def _vector_retrieval(
        self, request: SearchRequest, query_vector: List[float]
    ) -> Dict[uuid.UUID, CandidateMatch]:
        """Retrieves semantic candidates using pgvector cosine distance or in-memory fallback."""
        candidates: Dict[uuid.UUID, CandidateMatch] = {}
        try:
            distance_col = ChunkEmbedding.embedding.cosine_distance(query_vector).label("distance")
            stmt = (
                select(
                    DocumentChunk.document_id,
                    DocumentChunk.chunk_index,
                    DocumentChunk.page_number,
                    DocumentChunk.content,
                    distance_col,
                )
                .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(ChunkEmbedding.is_active == True)
            )
            stmt = self._build_metadata_filters(request, stmt)
            stmt = stmt.order_by(distance_col.asc()).limit(60)

            results = (await self.session.execute(stmt)).all()
            rank = 1
            for row in results:
                doc_id = row.document_id
                sim = max(0.0, 1.0 - float(row.distance))
                if doc_id not in candidates or sim > candidates[doc_id].score:
                    candidates[doc_id] = CandidateMatch(
                        document_id=doc_id,
                        rank=rank,
                        score=round(sim, 4),
                        chunk_index=row.chunk_index,
                        page_number=row.page_number,
                        content=row.content or "",
                        match_type="semantic",
                    )
                    rank += 1
        except Exception:
            # Fallback for SQLite / offline test environments without pgvector C extension
            candidates = await self._in_memory_vector_retrieval(request, query_vector)

        return candidates

    async def _in_memory_vector_retrieval(
        self, request: SearchRequest, query_vector: List[float]
    ) -> Dict[uuid.UUID, CandidateMatch]:
        """In-memory cosine similarity fallback."""
        stmt = (
            select(DocumentChunk, ChunkEmbedding, Document)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(ChunkEmbedding.is_active == True)
        )
        stmt = self._build_metadata_filters(request, stmt)
        rows = (await self.session.execute(stmt)).all()

        def cosine_sim(v1: List[float], v2: List[float]) -> float:
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        scored: List[Tuple[float, Any, Any]] = []
        for chunk, emb, doc in rows:
            vec = list(emb.embedding) if hasattr(emb.embedding, "__iter__") else []
            sim = cosine_sim(query_vector, vec)
            scored.append((sim, chunk, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        candidates: Dict[uuid.UUID, CandidateMatch] = {}
        rank = 1
        for sim, chunk, doc in scored:
            doc_id = chunk.document_id
            if doc_id not in candidates:
                candidates[doc_id] = CandidateMatch(
                    document_id=doc_id,
                    rank=rank,
                    score=round(sim, 4),
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    content=chunk.content or "",
                    match_type="semantic",
                )
                rank += 1
            if len(candidates) >= 60:
                break

        return candidates

    async def _keyword_retrieval(
        self, request: SearchRequest, query_str: str
    ) -> Dict[uuid.UUID, CandidateMatch]:
        """Retrieves keyword candidates using PostgreSQL ILIKE / full-text matches."""
        candidates: Dict[uuid.UUID, CandidateMatch] = {}
        tokens = [t.lower() for t in query_str.split() if len(t) > 1]
        if not tokens:
            return candidates

        # 1. Search chunks
        chunk_filters = [DocumentChunk.content.ilike(f"%{tok}%") for tok in tokens]
        chunk_stmt = (
            select(
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.page_number,
                DocumentChunk.content,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(or_(*chunk_filters))
        )
        chunk_stmt = self._build_metadata_filters(request, chunk_stmt)
        chunk_stmt = chunk_stmt.limit(100)

        chunk_results = (await self.session.execute(chunk_stmt)).all()

        # 2. Search document title/description directly
        doc_filters = [
            or_(
                Document.title.ilike(f"%{tok}%"),
                Document.description.ilike(f"%{tok}%"),
            )
            for tok in tokens
        ]
        doc_stmt = select(Document).where(or_(*doc_filters))
        doc_stmt = self._build_metadata_filters(request, doc_stmt)
        doc_stmt = doc_stmt.limit(50)

        doc_results = (await self.session.execute(doc_stmt)).scalars().all()

        # Score candidate relevance based on keyword hit count
        doc_scores: Dict[uuid.UUID, Dict[str, Any]] = {}

        for doc in doc_results:
            title_hits = sum(1 for tok in tokens if tok in (doc.title or "").lower())
            desc_hits = sum(1 for tok in tokens if tok in (doc.description or "").lower())
            score = (title_hits * 2.0) + desc_hits
            doc_scores[doc.id] = {
                "score": score,
                "chunk_index": 0,
                "page_number": 1,
                "content": doc.description or doc.title,
                "matched_fields": ["title"] if title_hits > 0 else ["description"],
            }

        for row in chunk_results:
            content_lower = (row.content or "").lower()
            hits = sum(1 for tok in tokens if tok in content_lower)
            if row.document_id not in doc_scores:
                doc_scores[row.document_id] = {
                    "score": hits,
                    "chunk_index": row.chunk_index,
                    "page_number": row.page_number,
                    "content": row.content or "",
                    "matched_fields": ["content"],
                }
            else:
                doc_scores[row.document_id]["score"] += hits
                if not doc_scores[row.document_id].get("content"):
                    doc_scores[row.document_id]["content"] = row.content

        # Rank candidates
        sorted_candidates = sorted(doc_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        rank = 1
        for doc_id, data in sorted_candidates:
            candidates[doc_id] = CandidateMatch(
                document_id=doc_id,
                rank=rank,
                score=float(data["score"]),
                chunk_index=data["chunk_index"],
                page_number=data["page_number"],
                content=data["content"],
                match_type="keyword",
                matched_fields=data.get("matched_fields", []),
            )
            rank += 1

        return candidates

    def _matches_post_filters(self, doc: Document, request: SearchRequest) -> Tuple[bool, Dict[str, Any]]:
        """Validates fine-grained archival metadata filters and records matched attributes."""
        matched_meta: Dict[str, Any] = {}
        meta = doc.doc_metadata

        # 1. Creator filter
        if request.creator:
            req_c = request.creator.lower()
            found = False
            if meta and meta.creators:
                for c in meta.creators:
                    c_name = c.get("name", "") if isinstance(c, dict) else str(c)
                    if req_c in c_name.lower():
                        found = True
                        matched_meta["creator"] = c_name
                        break
            if not found:
                return False, {}

        # 2. Subject filter
        if request.subject:
            req_s = request.subject.lower()
            found = False
            if meta and meta.subjects:
                for s in meta.subjects:
                    if req_s in str(s).lower():
                        found = True
                        matched_meta["subject"] = s
                        break
            if not found:
                return False, {}

        # 3. Date range filters
        if request.date_start or request.date_end:
            raw_date = meta.date_raw if meta else ""
            year_match = re.search(r"\b(1\d{3}|20\d{2})\b", raw_date or "")
            if year_match:
                doc_year = int(year_match.group(1))
                if request.date_start:
                    start_year_m = re.search(r"\b(1\d{3}|20\d{2})\b", request.date_start)
                    if start_year_m and doc_year < int(start_year_m.group(1)):
                        return False, {}
                if request.date_end:
                    end_year_m = re.search(r"\b(1\d{3}|20\d{2})\b", request.date_end)
                    if end_year_m and doc_year > int(end_year_m.group(1)):
                        return False, {}
                matched_meta["date"] = raw_date
            elif request.date_start and not raw_date:
                # If date range required but document has no date, filter out
                return False, {}

        # 4. Historical Period filter
        if request.historical_period:
            req_hp = request.historical_period.lower()
            ai_meta = (meta.ai_metadata or {}) if meta else {}
            hp = str(ai_meta.get("historical_period", "")).lower()
            if req_hp not in hp:
                return False, {}
            matched_meta["historical_period"] = ai_meta.get("historical_period")

        # 5. Entity Name filter
        if request.entity_name:
            req_ent = request.entity_name.lower()
            found = False
            for de in doc.entities:
                if de.entity and req_ent in de.entity.name.lower():
                    found = True
                    matched_meta["entity"] = de.entity.name
                    break
            if not found:
                return False, {}

        # Record date if present
        if meta and meta.date_raw and "date" not in matched_meta:
            matched_meta["date"] = meta.date_raw

        return True, matched_meta

    async def hybrid_search(
        self,
        request: SearchRequest,
        query_vector: Optional[List[float]] = None,
        normalized_query: Optional[str] = None,
    ) -> SearchResponse:
        """
        Executes unified hybrid search combining semantic vector retrieval,
        PostgreSQL keyword retrieval, metadata filtering, and modular score fusion.
        """
        start_time = time.perf_counter()
        q_str = normalized_query or request.query.strip()

        # 1. Semantic Vector Retrieval
        semantic_candidates: Dict[uuid.UUID, CandidateMatch] = {}
        if query_vector and request.search_type in ["hybrid", "semantic"]:
            semantic_candidates = await self._vector_retrieval(request, query_vector)

        # 2. Keyword / Full-Text Retrieval
        keyword_candidates: Dict[uuid.UUID, CandidateMatch] = {}
        if request.search_type in ["hybrid", "keyword"]:
            keyword_candidates = await self._keyword_retrieval(request, q_str)

        # 3. Modular Score Fusion & Ranking
        ranked_doc_tuples = self.ranker.rank(
            semantic_candidates=semantic_candidates,
            keyword_candidates=keyword_candidates,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight,
            limit=request.limit * 2,  # Fetch extra to account for post-filtering
            offset=0,
        )

        # 4. Result Hydration & Archival Metadata Filtering
        results: List[SearchResultItem] = []
        total_matching = 0

        for doc_id, score in ranked_doc_tuples:
            doc_stmt = (
                select(Document)
                .where(Document.id == doc_id)
                .options(
                    selectinload(Document.doc_metadata),
                    selectinload(Document.media_assets),
                    selectinload(Document.entities).selectinload(DocumentEntity.entity),
                )
            )
            doc = (await self.session.execute(doc_stmt)).scalar_one_or_none()
            if not doc:
                continue

            # Validate fine-grained metadata filters
            passes, matched_meta = self._matches_post_filters(doc, request)
            if not passes:
                continue

            total_matching += 1

            # Candidate details
            sem_cand = semantic_candidates.get(doc_id)
            kw_cand = keyword_candidates.get(doc_id)

            best_content = ""
            chunk_idx = None
            page_num = None
            if sem_cand and sem_cand.content:
                best_content = sem_cand.content
                chunk_idx = sem_cand.chunk_index
                page_num = sem_cand.page_number
            elif kw_cand and kw_cand.content:
                best_content = kw_cand.content
                chunk_idx = kw_cand.chunk_index
                page_num = kw_cand.page_number

            snippet = self._extract_snippet(
                best_content or doc.description or doc.title,
                q_str,
            )

            # Preview information from primary media asset
            preview_info = PreviewInformation()
            if doc.media_assets:
                primary_asset = next(
                    (a for a in doc.media_assets if a.asset_role == "primary"),
                    doc.media_assets[0],
                )
                preview_info = PreviewInformation(
                    has_media=True,
                    media_type=primary_asset.media_type,
                    mime_type=primary_asset.mime_type,
                    storage_key=primary_asset.storage_key,
                    access_url=doc.source_url,
                    page_number=page_num or primary_asset.page_number,
                    file_size_bytes=primary_asset.file_size_bytes,
                )

            # Entities
            entity_items = [
                MatchedEntityItem(
                    name=de.entity.name,
                    entity_type=de.entity.entity_type,
                    confidence=de.confidence,
                )
                for de in doc.entities
                if de.entity
            ]

            # Explanation
            explanations = []
            if sem_cand:
                explanations.append(f"Semantic match (sim: {sem_cand.score:.2f}, rank #{sem_cand.rank})")
            if kw_cand:
                explanations.append(f"Keyword match (rank #{kw_cand.rank})")
            explanation = " + ".join(explanations) if explanations else "Metadata match"

            # Document container
            doc_summary = DocumentSummary(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                source=doc.source,
                source_id=doc.source_id,
                record_type=doc.record_type,
                source_url=doc.source_url,
                status=doc.status,
            )

            result_item = SearchResultItem(
                document=doc_summary,
                relevance_score=score,
                matching_snippet=snippet,
                matched_metadata=matched_meta,
                source=doc.source,
                entities=entity_items,
                available_preview_information=preview_info,
                relevance_explanation=explanation,
                semantic_rank=sem_cand.rank if sem_cand else None,
                keyword_rank=kw_cand.rank if kw_cand else None,
                matching_chunk_index=chunk_idx,
                page_number=page_num,
            )
            results.append(result_item)

            if len(results) >= request.limit:
                break

        elapsed = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            search_type=request.search_type,
            total_results=total_matching,
            execution_time_ms=round(elapsed, 2),
            results=results[request.offset : request.offset + request.limit],
            facets={
                "sources": list({item.source for item in results}),
                "record_types": list({item.document.record_type for item in results}),
            },
        )
