import logging
from typing import Optional

from ai.interfaces.extractor import AIEnrichmentProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.mock_provider import MockLLMProvider
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def create_enrichment_provider(
    provider_type: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> AIEnrichmentProvider:
    """
    Factory creating an AI enrichment provider based on configuration.
    Business logic depends strictly on AIEnrichmentProvider, never on vendor classes.
    """
    chosen_provider = (provider_type or settings.AI_PROVIDER).lower().strip()

    if chosen_provider == "gemini":
        key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if key:
            model_name = model or "gemini-2.5-flash"
            logger.info(f"Initialized Gemini AI Enrichment Provider with model '{model_name}'.")
            return GeminiProvider(api_key=key, model=model_name)
        else:
            logger.warning(
                "AI_PROVIDER is set to 'gemini' but GEMINI_API_KEY is empty. "
                "Defaulting to MockLLMProvider."
            )

    logger.info("Initialized MockLLMProvider (deterministic historical NLP).")
    return MockLLMProvider()
