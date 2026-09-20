import logging
from typing import List

from ai.base import EmbeddingProvider
from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Embedding Provider using SentenceTransformers (default: all-MiniLM-L6-v2, 384 dimensions).
    Automatically falls back to MockEmbeddingProvider if PyTorch / SentenceTransformers is not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._fallback = None

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.warning(
                f"SentenceTransformer({model_name}) not loaded: {e}. "
                "Using MockEmbeddingProvider fallback."
            )
            self._fallback = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
            self._dim = settings.EMBEDDING_DIMENSION

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self._fallback is not None:
            return await self._fallback.embed_texts(texts)

        # Generate embeddings using sentence-transformers
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()
