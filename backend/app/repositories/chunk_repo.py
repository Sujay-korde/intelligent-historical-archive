import math
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from processing.chunking.base import ChunkDTO, EmbeddedChunkDTO


class ChunkRepository:
    """
    Repository for managing DocumentChunk and ChunkEmbedding entities in PostgreSQL (pgvector).
    Maintains clean separation between chunks and embeddings to support evolving models
    without database redesign.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_chunks_and_embeddings(
        self,
        document_id: uuid.UUID,
        chunks: List[ChunkDTO],
        embeddings: List[List[float]],
        model_name: str,
        model_version: str,
        dimension: int,
    ) -> List[EmbeddedChunkDTO]:
        """
        Persists chunks and vector embeddings, returning structured EmbeddedChunkDTO records.
        """
        created_dtos: List[EmbeddedChunkDTO] = []

        for chunk_dto, emb_vector in zip(chunks, embeddings):
            chunk_uuid = chunk_dto.chunk_id or uuid.uuid4()
            doc_chunk = DocumentChunk(
                id=chunk_uuid,
                document_id=document_id,
                chunk_index=chunk_dto.chunk_index,
                content=chunk_dto.content,
                page_number=chunk_dto.page_number,
                token_count=chunk_dto.token_count,
            )
            self.session.add(doc_chunk)

            chunk_emb = ChunkEmbedding(
                id=uuid.uuid4(),
                chunk_id=chunk_uuid,
                model_name=model_name,
                model_version=model_version,
                dimension=dimension,
                embedding=emb_vector,
                is_active=True,
            )
            self.session.add(chunk_emb)

            created_dtos.append(
                EmbeddedChunkDTO(
                    document_id=document_id,
                    chunk_id=chunk_uuid,
                    chunk_index=chunk_dto.chunk_index,
                    content=chunk_dto.content,
                    page_number=chunk_dto.page_number,
                    token_count=chunk_dto.token_count,
                    embedding=emb_vector,
                    embedding_model=model_name,
                    embedding_model_version=model_version,
                )
            )

        await self.session.flush()
        return created_dtos

    async def get_chunks_by_document(self, document_id: uuid.UUID) -> List[DocumentChunk]:
        """Retrieve all raw chunks for a given document."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_embedded_chunks_by_document(
        self, document_id: uuid.UUID, model_name: Optional[str] = None
    ) -> List[EmbeddedChunkDTO]:
        """
        Retrieve chunks with their active embeddings and model metadata.
        """
        stmt = (
            select(DocumentChunk, ChunkEmbedding)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
            .where(DocumentChunk.document_id == document_id)
        )
        if model_name:
            stmt = stmt.where(ChunkEmbedding.model_name == model_name)
        else:
            stmt = stmt.where(ChunkEmbedding.is_active == True)

        stmt = stmt.order_by(DocumentChunk.chunk_index.asc())
        result = await self.session.execute(stmt)
        rows = result.all()

        embedded_chunks: List[EmbeddedChunkDTO] = []
        for chunk, emb in rows:
            # emb.embedding may be a list, numpy array, or pgvector Vector object
            emb_list = list(emb.embedding) if hasattr(emb.embedding, "__iter__") else []
            embedded_chunks.append(
                EmbeddedChunkDTO(
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    embedding=emb_list,
                    embedding_model=emb.model_name,
                    embedding_model_version=emb.model_version,
                    created_at=chunk.created_at,
                )
            )
        return embedded_chunks

    async def vector_similarity_search(
        self,
        query_vector: List[float],
        limit: int = 10,
        model_name: Optional[str] = None,
        source: Optional[str] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs cosine similarity search using pgvector with graceful fallback.
        """
        try:
            # pgvector cosine distance operator
            distance_col = ChunkEmbedding.embedding.cosine_distance(query_vector).label("distance")
            stmt = (
                select(
                    DocumentChunk.document_id,
                    DocumentChunk.id.label("chunk_id"),
                    DocumentChunk.chunk_index,
                    DocumentChunk.page_number,
                    DocumentChunk.content,
                    ChunkEmbedding.model_name,
                    ChunkEmbedding.model_version,
                    distance_col,
                    Document.title,
                    Document.source,
                )
                .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .outerjoin(Document, Document.id == DocumentChunk.document_id)
                .where(ChunkEmbedding.is_active == True)
            )

            if model_name:
                stmt = stmt.where(ChunkEmbedding.model_name == model_name)
            if source:
                stmt = stmt.where(Document.source == source)

            stmt = stmt.order_by(distance_col.asc()).limit(limit * 2)
            results = (await self.session.execute(stmt)).all()

            matches = []
            for row in results:
                dist = float(row.distance)
                sim = max(0.0, 1.0 - dist)
                if min_similarity is None or sim >= min_similarity:
                    matches.append({
                        "document_id": row.document_id,
                        "chunk_id": row.chunk_id,
                        "chunk_index": row.chunk_index,
                        "page_number": row.page_number,
                        "content": row.content,
                        "similarity": round(sim, 4),
                        "distance": round(dist, 4),
                        "model_name": row.model_name,
                        "model_version": row.model_version,
                        "title": row.title,
                        "source": row.source,
                    })
                    if len(matches) >= limit:
                        break
            return matches

        except Exception:
            # Fallback for offline/SQLite test environments without pgvector C extension
            return await self._in_memory_similarity_search(
                query_vector=query_vector,
                limit=limit,
                model_name=model_name,
                source=source,
                min_similarity=min_similarity,
            )

    async def _in_memory_similarity_search(
        self,
        query_vector: List[float],
        limit: int = 10,
        model_name: Optional[str] = None,
        source: Optional[str] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """In-memory cosine similarity fallback."""
        stmt = (
            select(DocumentChunk, ChunkEmbedding, Document)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
            .outerjoin(Document, Document.id == DocumentChunk.document_id)
            .where(ChunkEmbedding.is_active == True)
        )
        if model_name:
            stmt = stmt.where(ChunkEmbedding.model_name == model_name)
        if source:
            stmt = stmt.where(Document.source == source)

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

        scored = []
        for chunk, emb, doc in rows:
            vec = list(emb.embedding) if hasattr(emb.embedding, "__iter__") else []
            sim = cosine_sim(query_vector, vec)
            if min_similarity is None or sim >= min_similarity:
                scored.append({
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                    "similarity": round(sim, 4),
                    "distance": round(1.0 - sim, 4),
                    "model_name": emb.model_name,
                    "model_version": emb.model_version,
                    "title": doc.title if doc else None,
                    "source": doc.source if doc else None,
                })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:limit]
        return scored[:limit]
