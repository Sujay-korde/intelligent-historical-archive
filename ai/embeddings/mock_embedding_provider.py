import hashlib
import math
from typing import List

from ai.base import EmbeddingProvider
from backend.app.core.config import settings


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, zero-dependency embedding provider.
    Uses feature hashing and n-gram projections to generate unit-normalized vectors.
    Texts with common words or character n-grams yield higher cosine similarity.
    """

    def __init__(
        self,
        dimension: int = settings.EMBEDDING_DIMENSION,
        model_name: str = "mock-feature-hash-v1",
        model_version: str = "1.0.0",
    ):
        self._dim = dimension
        self._model_name = model_name
        self._model_version = model_version

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def _hash_token(self, token: str, dim: int) -> int:
        # Hash a token into an index [0, dim - 1]
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        return h % dim

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        words = text.lower().split()
        if not words:
            # Return normalized uniform vector if empty
            val = 1.0 / math.sqrt(self._dim)
            return [val] * self._dim

        for i, word in enumerate(words):
            idx = self._hash_token(word, self._dim)
            sign = 1.0 if (hash(word) % 2 == 0) else -1.0
            vec[idx] += sign

            # Also hash 3-grams for subword similarity
            if len(word) >= 3:
                for k in range(len(word) - 2):
                    trigram = word[k : k + 3]
                    tri_idx = self._hash_token(trigram, self._dim)
                    vec[tri_idx] += 0.5 * sign

        # L2 Normalize vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            val = 1.0 / math.sqrt(self._dim)
            vec = [val] * self._dim

        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]
