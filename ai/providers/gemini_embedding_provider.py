import asyncio
import logging
import math
from typing import List, Optional
import httpx

from ai.interfaces.embedding import EmbeddingProvider
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Real Embedding Provider using Google Gemini REST API.
    Uses 'gemini-embedding-001' (also supporting 'text-embedding-004' as alias)
    with native outputDimensionality support (defaults to 768).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        raw_model = model or getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")
        # In 2026 API, text-embedding-004 is succeeded by gemini-embedding-001
        if "text-embedding-004" in raw_model:
            logger.info("Mapping 'text-embedding-004' to supported active model 'gemini-embedding-001'")
            self._model = "gemini-embedding-001"
        else:
            self._model = raw_model

        self._dimension = dimension or getattr(settings, "EMBEDDING_DIMENSION", 768)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def _embed_single(self, client: httpx.AsyncClient, text: str) -> List[float]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self._dimension,
        }

        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 503 or resp.status_code == 429:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                values = data.get("embedding", {}).get("values", [])
                if not values:
                    raise ValueError(f"Empty embedding returned by {self._model}")

                # Ensure exact requested dimension
                if len(values) != self._dimension:
                    logger.warning(
                        f"Expected dimension {self._dimension} but received {len(values)}. Adjusting."
                    )
                    if len(values) > self._dimension:
                        values = values[: self._dimension]

                # L2 normalize
                norm = math.sqrt(sum(x * x for x in values)) or 1.0
                return [round(x / norm, 6) for x in values]
            except Exception as e:
                if attempt == 2:
                    raise e
                await asyncio.sleep(1.0 * (attempt + 1))

        raise RuntimeError(f"Failed to generate embedding after retries for text: {text[:50]}...")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [self._embed_single(client, t) for t in texts]
            return await asyncio.gather(*tasks)
