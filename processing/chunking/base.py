from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from processing.base import ExtractedContent


class ChunkDTO(BaseModel):
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    token_count: int


class Chunker(ABC):
    @abstractmethod
    def chunk(
        self, content: ExtractedContent, max_tokens: int = 500, overlap: int = 50
    ) -> List[ChunkDTO]:
        """Split document content into structured chunks."""
        pass
