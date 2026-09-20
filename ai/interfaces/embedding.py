from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """
    Abstract interface for text embedding providers (SentenceTransformers, Gemini, OpenAI, Mock).
    Decouples embedding generation from business logic and pgvector storage.
    """

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-embed multiple text strings into normalized float vectors.
        """
        pass

    async def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string.
        """
        results = await self.embed_texts([text])
        return results[0]

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality (e.g., 384, 768, 1536)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Release version tag of the embedding model."""
        pass
