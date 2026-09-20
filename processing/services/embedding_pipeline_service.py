import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai.embeddings.factory import create_embedding_provider
from ai.interfaces.embedding import EmbeddingProvider
from backend.app.core.config import settings
from backend.app.repositories.chunk_repo import ChunkRepository
from processing.base import ExtractedContent, ExtractedPage
from processing.chunking.base import BaseChunker, ChunkDTO, EmbeddedChunkDTO
from processing.chunking.factory import get_chunker
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class EmbeddingPipelineService:
    """
    Orchestrator for the document embedding lifecycle:
    processed document
    → clean text
    → semantic chunks
    → embedding model
    → pgvector storage
    → similarity search

    Strictly retains for each chunk:
    - document_id
    - chunk_id
    - chunk_index
    - content
    - page_number
    - embedding
    - embedding_model
    - embedding_model_version
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunker: Optional[BaseChunker] = None,
        chunk_repo: Optional[ChunkRepository] = None,
    ):
        self.session = session
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.chunker = chunker or get_chunker("paragraph")
        self.chunk_repo = chunk_repo or ChunkRepository(session)

    def create_chunks(
        self,
        content: ExtractedContent,
        max_tokens: int = settings.MAX_CHUNK_TOKENS,
        overlap: int = settings.CHUNK_OVERLAP_TOKENS,
    ) -> List[ChunkDTO]:
        """
        Splits extracted document content into structured semantic chunks using the configured chunker.
        Cleans and normalizes text before chunking.
        """
        # Ensure text is normalized
        normalized_pages = [
            ExtractedPage(
                page_number=p.page_number,
                text=normalize_archival_text(p.text),
                has_images=p.has_images,
                ocr_applied=p.ocr_applied,
            )
            for p in content.pages
        ]
        clean_content = ExtractedContent(
            pages=normalized_pages,
            total_pages=content.total_pages,
            full_text=normalize_archival_text(content.full_text),
            detected_language=content.detected_language,
        )
        chunks = self.chunker.chunk(clean_content, max_tokens=max_tokens, overlap=overlap)
        logger.info(
            f"Created {len(chunks)} chunks using strategy '{self.chunker.strategy_name}'."
        )
        return chunks

    async def generate_embeddings(self, chunks: List[ChunkDTO]) -> List[List[float]]:
        """
        Generates dense vector representations for all chunks using the configured EmbeddingProvider.
        """
        if not chunks:
            return []

        texts = [c.content for c in chunks]
        embeddings = await self.embedding_provider.embed_texts(texts)
        logger.info(
            f"Generated {len(embeddings)} vectors with model '{self.embedding_provider.model_name}' "
            f"v{self.embedding_provider.model_version} ({self.embedding_provider.dimension} dims)."
        )
        return embeddings

    async def store_in_pgvector(
        self,
        document_id: uuid.UUID,
        chunks: List[ChunkDTO],
        embeddings: List[List[float]],
    ) -> List[EmbeddedChunkDTO]:
        """
        Persists chunks and vectors into PostgreSQL / pgvector.
        Returns the complete EmbeddedChunkDTO instances.
        """
        return await self.chunk_repo.save_chunks_and_embeddings(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            model_name=self.embedding_provider.model_name,
            model_version=self.embedding_provider.model_version,
            dimension=self.embedding_provider.dimension,
        )

    async def process_document_embeddings(
        self,
        document_id: uuid.UUID,
        content: ExtractedContent,
        max_tokens: int = settings.MAX_CHUNK_TOKENS,
        overlap: int = settings.CHUNK_OVERLAP_TOKENS,
    ) -> List[EmbeddedChunkDTO]:
        """
        Executes the full pipeline:
        processed document
        → clean text
        → semantic chunks
        → embedding model
        → pgvector
        """
        chunks = self.create_chunks(content, max_tokens=max_tokens, overlap=overlap)
        embeddings = await self.generate_embeddings(chunks)
        embedded_chunks = await self.store_in_pgvector(document_id, chunks, embeddings)
        await self.session.commit()
        return embedded_chunks

    async def similarity_search(
        self,
        query: str,
        limit: int = 10,
        source: Optional[str] = None,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Embeds query text and performs vector similarity search across pgvector chunks.
        """
        clean_query = normalize_archival_text(query)
        query_vector = await self.embedding_provider.embed_text(clean_query)

        return await self.chunk_repo.vector_similarity_search(
            query_vector=query_vector,
            limit=limit,
            model_name=self.embedding_provider.model_name,
            source=source,
            min_similarity=min_similarity,
        )
