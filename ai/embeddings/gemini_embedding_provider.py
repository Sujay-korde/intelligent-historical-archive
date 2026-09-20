import logging
from typing import List, Optional

from ai.base import EmbeddingProvider
from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Embedding Provider using Google Gemini text-embedding-004 (768 dimensions).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-004"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self._fallback = MockEmbeddingProvider(dimension=768)

    @property
    def dimension(self) -> int:
        return 768

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            result = client.models.embed_content(
                model=self.model,
                contents=texts,
            )
            embeddings = [e.values for e in result.embeddings]
            return embeddings
        except Exception as e:
            logger.warning(f"Gemini embed_texts failed ({e}). Using Mock fallback.")
            return await self._fallback.embed_texts(texts)
