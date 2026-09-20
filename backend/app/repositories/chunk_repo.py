import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from processing.chunking.base import ChunkDTO


class ChunkRepository:
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
    ) -> List[DocumentChunk]:
        created_chunks: List[DocumentChunk] = []

        for chunk_dto, emb_vector in zip(chunks, embeddings):
            doc_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_dto.chunk_index,
                content=chunk_dto.content,
                page_number=chunk_dto.page_number,
                token_count=chunk_dto.token_count,
            )
            self.session.add(doc_chunk)
            await self.session.flush()

            chunk_emb = ChunkEmbedding(
                chunk_id=doc_chunk.id,
                model_name=model_name,
                model_version=model_version,
                dimension=dimension,
                embedding=emb_vector,
                is_active=True,
            )
            self.session.add(chunk_emb)
            created_chunks.append(doc_chunk)

        await self.session.flush()
        return created_chunks

    async def get_chunks_by_document(self, document_id: uuid.UUID) -> List[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
