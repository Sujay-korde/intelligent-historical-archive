import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from processing.base import ExtractedContent, ExtractedPage


class ChunkDTO(BaseModel):
    """
    Data transfer object representing a chunk of text prior to embedding.
    """
    chunk_index: int = Field(description="Zero-based sequence index within the document.")
    content: str = Field(description="Normalized text content of the chunk.")
    page_number: Optional[int] = Field(default=None, description="Page number of origin if available.")
    token_count: int = Field(default=0, description="Estimated token count.")
    chunk_id: Optional[uuid.UUID] = Field(default=None, description="Assigned unique chunk UUID.")
    document_id: Optional[uuid.UUID] = Field(default=None, description="Parent document UUID.")


class EmbeddedChunkDTO(BaseModel):
    """
    Structured representation of a document chunk retaining all provenance and vector attributes.
    """
    document_id: uuid.UUID = Field(description="Foreign key linking to parent Document.")
    chunk_id: uuid.UUID = Field(description="Unique identifier for the chunk.")
    chunk_index: int = Field(description="Sequential position of chunk within the document.")
    content: str = Field(description="Extracted and normalized chunk text.")
    page_number: Optional[int] = Field(default=None, description="Archival page number where available.")
    token_count: Optional[int] = Field(default=None, description="Token count.")
    embedding: List[float] = Field(description="Vector embedding generated for the chunk.")
    embedding_model: str = Field(description="Name of model used to produce the vector.")
    embedding_model_version: Optional[str] = Field(default=None, description="Model version tag.")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes DTO to a dictionary representation."""
        d = self.model_dump()
        d["document_id"] = str(self.document_id)
        d["chunk_id"] = str(self.chunk_id)
        return d

    def to_search_result(self, similarity: float, distance: Optional[float] = None) -> Dict[str, Any]:
        """Converts embedded chunk into a standardized search result dictionary."""
        return {
            "document_id": str(self.document_id),
            "chunk_id": str(self.chunk_id),
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "content": self.content,
            "similarity": round(similarity, 4),
            "distance": round(distance if distance is not None else (1.0 - similarity), 4),
            "model_name": self.embedding_model,
            "model_version": self.embedding_model_version,
        }


class BaseChunker(ABC):
    """
    Abstract interface for document chunking strategies.
    Allows changing or configuring chunking algorithms (paragraph, page-level, fixed window, etc.)
    without modifying core pipeline or storage code.
    """
    strategy_name: str = "BaseChunker"

    @abstractmethod
    def chunk(
        self, content: ExtractedContent, max_tokens: int = 500, overlap: int = 50
    ) -> List[ChunkDTO]:
        """Split document content into structured chunks."""
        pass

    def chunk_text(
        self, text: str, max_tokens: int = 500, overlap: int = 50
    ) -> List[ChunkDTO]:
        """Convenience method to chunk raw text directly."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            return []
        content = ExtractedContent(
            pages=[ExtractedPage(page_number=1, text=clean_text)],
            total_pages=1,
            full_text=clean_text,
        )
        return self.chunk(content, max_tokens=max_tokens, overlap=overlap)


Chunker = BaseChunker

__all__ = [
    "ChunkDTO",
    "EmbeddedChunkDTO",
    "BaseChunker",
    "Chunker",
]
