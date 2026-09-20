import json
import logging
import time
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from ai.base import (
    AIResponse,
    ExtractedEntity,
    ExtractedMetadata,
    LLMProvider,
    TokenUsage,
)
from backend.app.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    LLM Provider using Google Gemini API.
    Supports structured JSON generation and summarization.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model

    async def extract_structured(
        self, prompt: str, schema: Type[T], context: Optional[Dict[str, Any]] = None
    ) -> AIResponse[T]:
        start = time.perf_counter()
        json_schema = schema.model_json_schema()

        system_instruction = (
            "You are an expert archival historian and knowledge extraction assistant. "
            "Analyze the provided historical text and extract structured metadata and knowledge entities. "
            "Output strictly valid JSON matching the provided schema."
        )

        full_prompt = (
            f"{system_instruction}\n\n"
            f"Schema:\n{json.dumps(json_schema, indent=2)}\n\n"
            f"Text to analyze:\n{prompt}"
        )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )

            latency = (time.perf_counter() - start) * 1000
            result_obj = schema.model_validate_json(response.text)

            prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            candidate_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0

            return AIResponse(
                data=result_obj,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=candidate_tokens,
                    total_tokens=prompt_tokens + candidate_tokens,
                ),
                model_name=self.model_name,
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}). Falling back to MockLLMProvider.")
            from ai.providers.mock_provider import MockLLMProvider
            fallback = MockLLMProvider()
            return await fallback.extract_structured(prompt, schema, context)

    async def summarize(self, text: str, max_length: int = 300) -> AIResponse[str]:
        start = time.perf_counter()
        prompt = f"Provide an archival summary of the following text in under {max_length} characters:\n\n{text}"

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            latency = (time.perf_counter() - start) * 1000
            summary = response.text.strip()
            prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            candidate_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0

            return AIResponse(
                data=summary,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=candidate_tokens,
                    total_tokens=prompt_tokens + candidate_tokens,
                ),
                model_name=self.model_name,
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            logger.warning(f"Gemini summarize failed ({e}). Falling back to MockLLMProvider.")
            from ai.providers.mock_provider import MockLLMProvider
            fallback = MockLLMProvider()
            return await fallback.summarize(text, max_length)
