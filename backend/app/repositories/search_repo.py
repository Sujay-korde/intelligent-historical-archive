import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.metadata import DocumentMetadata
from backend.app.schemas.search import SearchRequest, SearchResponse, SearchResultItem


class SearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _extract_snippet(self, content: str, query: str, max_chars: int = 240) -> str:
        """Extract a highlighted snippet centered around query terms."""
        content_clean = content.strip()
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

    async def hybrid_search(
        self, request: SearchRequest, query_vector: Optional[List[float]] = None
    ) -> SearchResponse:
        start_time = time.perf_counter()
        k_rrf = 60
        limit = request.limit
        query_str = request.query.strip()

        # 1. Semantic Search
        semantic_ranked_docs: Dict[uuid.UUID, Dict[str, Any]] = {}
        if query_vector and request.search_type in ["hybrid", "semantic"]:
            try:
                # Cosine distance via pgvector
                # ChunkEmbedding.embedding.cosine_distance(query_vector)
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

                if request.source:
                    stmt = stmt.where(Document.source == request.source)
                if request.record_type:
                    stmt = stmt.where(Document.record_type == request.record_type)

                stmt = stmt.order_by(distance_col.asc()).limit(50)
                results = (await self.session.execute(stmt)).all()

                rank = 1
                for row in results:
                    doc_id = row.document_id
                    sim_score = max(0.0, 1.0 - float(row.distance))
                    if doc_id not in semantic_ranked_docs or sim_score > semantic_ranked_docs[doc_id]["score"]:
                        semantic_ranked_docs[doc_id] = {
                            "rank": rank,
                            "score": sim_score,
                            "chunk_index": row.chunk_index,
                            "page_number": row.page_number,
                            "content": row.content,
                        }
                        rank += 1
            except Exception:
                # Fallback for offline/mock or if pgvector query fails
                pass

        # 2. Keyword / Full-Text Search
        keyword_ranked_docs: Dict[uuid.UUID, Dict[str, Any]] = {}
        if request.search_type in ["hybrid", "keyword"]:
            try:
                # Use ILIKE and ts_rank on Document and DocumentChunk
                kw_stmt = (
                    select(
                        DocumentChunk.document_id,
                        DocumentChunk.chunk_index,
                        DocumentChunk.page_number,
                        DocumentChunk.content,
                        Document.title,
                    )
                    .join(Document, Document.id == DocumentChunk.document_id)
                    .where(
                        or_(
                            DocumentChunk.content.ilike(f"%{query_str}%"),
                            Document.title.ilike(f"%{query_str}%"),
                            Document.description.ilike(f"%{query_str}%"),
                        )
                    )
                )

                if request.source:
                    kw_stmt = kw_stmt.where(Document.source == request.source)
                if request.record_type:
                    kw_stmt = kw_stmt.where(Document.record_type == request.record_type)

                kw_stmt = kw_stmt.limit(50)
                kw_results = (await self.session.execute(kw_stmt)).all()

                kw_rank = 1
                for row in kw_results:
                    doc_id = row.document_id
                    if doc_id not in keyword_ranked_docs:
                        keyword_ranked_docs[doc_id] = {
                            "rank": kw_rank,
                            "chunk_index": row.chunk_index,
                            "page_number": row.page_number,
                            "content": row.content,
                        }
                        kw_rank += 1
            except Exception:
                pass

        # 3. Reciprocal Rank Fusion (RRF)
        all_doc_ids = set(semantic_ranked_docs.keys()) | set(keyword_ranked_docs.keys())
        rrf_scores: Dict[uuid.UUID, float] = {}

        w_sem = request.semantic_weight if request.search_type == "hybrid" else (1.0 if request.search_type == "semantic" else 0.0)
        w_kw = request.keyword_weight if request.search_type == "hybrid" else (1.0 if request.search_type == "keyword" else 0.0)

        for doc_id in all_doc_ids:
            score = 0.0
            if doc_id in semantic_ranked_docs:
                sem_rank = semantic_ranked_docs[doc_id]["rank"]
                score += w_sem / (k_rrf + sem_rank)
            if doc_id in keyword_ranked_docs:
                kw_rank = keyword_ranked_docs[doc_id]["rank"]
                score += w_kw / (k_rrf + kw_rank)
            rrf_scores[doc_id] = score

        # Sort doc_ids by RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        # 4. Hydrate Document Details & Entities
        result_items: List[SearchResultItem] = []
        for doc_id, final_score in sorted_docs:
            doc_stmt = (
                select(Document)
                .where(Document.id == doc_id)
                .options(
                    selectinload(Document.doc_metadata),
                    selectinload(Document.entities).selectinload(DocumentEntity.entity),
                )
            )
            doc = (await self.session.execute(doc_stmt)).scalar_one_or_none()
            if not doc:
                continue

            # Pick best snippet
            best_chunk_content = ""
            matching_chunk_idx = None
            page_num = None
            if doc_id in semantic_ranked_docs:
                best_chunk_content = semantic_ranked_docs[doc_id]["content"]
                matching_chunk_idx = semantic_ranked_docs[doc_id]["chunk_index"]
                page_num = semantic_ranked_docs[doc_id]["page_number"]
            elif doc_id in keyword_ranked_docs:
                best_chunk_content = keyword_ranked_docs[doc_id]["content"]
                matching_chunk_idx = keyword_ranked_docs[doc_id]["chunk_index"]
                page_num = keyword_ranked_docs[doc_id]["page_number"]

            snippet = self._extract_snippet(best_chunk_content or doc.description or doc.title, query_str)

            # Entity names
            entity_names = [de.entity.name for de in doc.entities if de.entity]

            # Explanation
            sem_info = semantic_ranked_docs.get(doc_id)
            kw_info = keyword_ranked_docs.get(doc_id)
            explanations = []
            if sem_info:
                explanations.append(f"Semantic match (sim: {sem_info['score']:.2f}, rank #{sem_info['rank']})")
            if kw_info:
                explanations.append(f"Keyword match (rank #{kw_info['rank']})")
            relevance = " + ".join(explanations) if explanations else "Matched query filters"

            date_str = doc.doc_metadata.date_raw if doc.doc_metadata else None

            result_items.append(
                SearchResultItem(
                    document_id=doc.id,
                    title=doc.title,
                    source=doc.source,
                    source_id=doc.source_id,
                    date=date_str,
                    record_type=doc.record_type,
                    score=round(final_score, 4),
                    semantic_rank=sem_info["rank"] if sem_info else None,
                    keyword_rank=kw_info["rank"] if kw_info else None,
                    snippet=snippet,
                    matching_chunk_index=matching_chunk_idx,
                    page_number=page_num,
                    entities=entity_names[:5],
                    source_url=doc.source_url,
                    relevance_explanation=relevance,
                )
            )

        elapsed = (time.perf_counter() - start_time) * 1000
        return SearchResponse(
            query=query_str,
            search_type=request.search_type,
            total_results=len(all_doc_ids),
            execution_time_ms=round(elapsed, 2),
            results=result_items,
            facets={
                "sources": list({item.source for item in result_items}),
                "record_types": list({item.record_type for item in result_items}),
            },
        )
