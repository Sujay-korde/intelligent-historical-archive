import logging
from typing import Optional

from ai.interfaces.embedding import EmbeddingProvider
from ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider
from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from ai.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def create_embedding_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
    dimension: Optional[int] = None,
) -> EmbeddingProvider:
    """
    Factory creating an embedding provider based on application configuration.
    Business logic and repositories depend strictly on EmbeddingProvider,
    never on specific vendor classes.
    """
    chosen = (provider_type or settings.EMBEDDING_PROVIDER).lower().strip()

    if chosen == "sentence_transformers":
        model = model_name or settings.EMBEDDING_MODEL
        logger.info(f"Instantiating SentenceTransformerProvider with model '{model}'.")
        return SentenceTransformerProvider(model_name=model)

    elif chosen == "gemini":
        key = settings.GEMINI_API_KEY
        if key:
            model = model_name or "text-embedding-004"
            logger.info(f"Instantiating GeminiEmbeddingProvider with model '{model}'.")
            return GeminiEmbeddingProvider(api_key=key, model=model)
        else:
            logger.warning("GEMINI_API_KEY is not set. Defaulting to MockEmbeddingProvider.")

    dim = dimension or settings.EMBEDDING_DIMENSION
    logger.info(f"Instantiating MockEmbeddingProvider (dimension={dim}).")
    return MockEmbeddingProvider(dimension=dim)
