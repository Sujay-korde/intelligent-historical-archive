import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel

from ai.interfaces.extractor import AIEnrichmentProvider
from ai.models.enrichment import (
    AIEnrichmentResult,
    AIEntity,
    AIMetadata,
    AIResponseEnvelope,
    AISummary,
    TokenUsage,
)
from ai.providers.mock_provider import MockLLMProvider
from ai.validation.model_validator import ModelOutputValidator
from backend.app.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIEnrichmentProvider):
    """
    LLM Provider using Google Gemini via direct REST API.
    Supports structured JSON generation, entity recognition, and summarization.
    Defensively validates output with ModelOutputValidator and falls back to MockLLM on failure.
    """
    provider_name: str = "Gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-flash-latest")
        self.fallback = MockLLMProvider()

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def model_version(self) -> Optional[str]:
        return "2026.09"

    async def _call_gemini_rest(self, prompt: str, schema_dict: Dict[str, Any]) -> str:
        """
        Executes REST call to Gemini generateContent endpoint with retry on temporary 503 capacity spikes.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        candidate_models = [self.model]
        for fallback_model in ["gemini-flash-lite-latest", "gemini-3.1-flash-lite"]:
            if fallback_model not in candidate_models:
                candidate_models.append(fallback_model)

        last_err = None
        for model_to_use in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    "You are an archival historian and knowledge extraction assistant. "
                                    "Analyze the provided historical document text and return strictly valid JSON matching this schema:\n"
                                    f"{json.dumps(schema_dict, indent=2)}\n\n"
                                    f"Text to analyze:\n{prompt}"
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                },
            }

            for attempt in range(2):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 503:
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                        resp.raise_for_status()
                        data = resp.json()

                    candidates = data.get("candidates", [])
                    if candidates and candidates[0].get("content", {}).get("parts"):
                        self.model = model_to_use
                        return candidates[0]["content"]["parts"][0].get("text", "")
                except Exception as e:
                    last_err = e
                    if attempt == 0:
                        await asyncio.sleep(1.0)

        raise last_err or ValueError("Failed to obtain response from Gemini.")

    async def extract_metadata(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIMetadata]:
        start = time.perf_counter()
        if not self.api_key:
            return await self.fallback.extract_metadata(text, context)

        try:
            raw_text = await self._call_gemini_rest(text, AIMetadata.model_json_schema())
            meta = ModelOutputValidator.parse_and_validate(raw_text, AIMetadata)
            latency = (time.perf_counter() - start) * 1000

            return AIResponseEnvelope(
                data=meta,
                provider=self.provider_name,
                model=self.model_name,
                model_version=self.model_version,
                confidence=meta.confidence,
                latency_ms=round(latency, 2),
                raw_output=raw_text,
                provenance="AI",
            )
        except Exception as e:
            logger.warning(f"Gemini metadata extraction failed ({e}). Falling back to MockLLM.")
            return await self.fallback.extract_metadata(text, context)

    async def extract_entities(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[List[AIEntity]]:
        start = time.perf_counter()
        if not self.api_key:
            return await self.fallback.extract_entities(text, context)

        try:
            schema = {"type": "array", "items": AIEntity.model_json_schema()}
            raw_text = await self._call_gemini_rest(text, schema)
            clean_json = ModelOutputValidator.clean_json_markdown(raw_text)
            parsed = json.loads(clean_json)
            entities = []
            if isinstance(parsed, list):
                for item in parsed:
                    e = ModelOutputValidator.sanitize_entity(item)
                    if e:
                        entities.append(e)

            latency = (time.perf_counter() - start) * 1000
            avg_conf = (
                sum(e.confidence for e in entities) / len(entities) if entities else 1.0
            )

            return AIResponseEnvelope(
                data=entities,
                provider=self.provider_name,
                model=self.model_name,
                model_version=self.model_version,
                confidence=round(avg_conf, 2),
                latency_ms=round(latency, 2),
                raw_output=raw_text,
                provenance="AI",
            )
        except Exception as e:
            logger.warning(f"Gemini entity extraction failed ({e}). Falling back to MockLLM.")
            return await self.fallback.extract_entities(text, context)

    async def summarize(
        self, text: str, max_length: int = 300
    ) -> AIResponseEnvelope[AISummary]:
        start = time.perf_counter()
        if not self.api_key:
            return await self.fallback.summarize(text, max_length)

        try:
            raw_text = await self._call_gemini_rest(text, AISummary.model_json_schema())
            summary = ModelOutputValidator.parse_and_validate(raw_text, AISummary)
            latency = (time.perf_counter() - start) * 1000

            return AIResponseEnvelope(
                data=summary,
                provider=self.provider_name,
                model=self.model_name,
                model_version=self.model_version,
                confidence=summary.confidence,
                latency_ms=round(latency, 2),
                raw_output=raw_text,
                provenance="AI",
            )
        except Exception as e:
            logger.warning(f"Gemini summarize failed ({e}). Falling back to MockLLM.")
            return await self.fallback.summarize(text, max_length)

    async def enrich(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIEnrichmentResult]:
        start = time.perf_counter()
        if not self.api_key:
            return await self.fallback.enrich(text, context)

        try:
            raw_text = await self._call_gemini_rest(text, AIEnrichmentResult.model_json_schema())
            result = ModelOutputValidator.parse_and_validate(raw_text, AIEnrichmentResult)
            latency = (time.perf_counter() - start) * 1000

            return AIResponseEnvelope(
                data=result,
                provider=self.provider_name,
                model=self.model_name,
                model_version=self.model_version,
                confidence=result.metadata.confidence,
                latency_ms=round(latency, 2),
                raw_output=raw_text,
                provenance="AI",
            )
        except Exception as e:
            logger.warning(f"Gemini enrichment failed ({e}). Falling back to MockLLM.")
            return await self.fallback.enrich(text, context)

    # Backwards compatibility helper for existing code calling extract_structured
    async def extract_structured(
        self, prompt: str, schema: Type[T], context: Optional[Dict[str, Any]] = None
    ) -> Any:
        return await self.fallback.extract_structured(prompt, schema, context)
