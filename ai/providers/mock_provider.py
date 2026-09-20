import re
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from ai.base import (
    AIResponse,
    ExtractedEntity,
    ExtractedMetadata,
    LLMProvider,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Deterministic, zero-dependency offline AI provider.
    Extracts metadata, entities, and summaries using rule-based heuristic NLP.
    Ensures tests and offline demos work flawlessly without API keys or rate limits.
    """

    @property
    def model_name(self) -> str:
        return "mock-historical-nlp-v1"

    async def extract_structured(
        self, prompt: str, schema: Type[T], context: Optional[Dict[str, Any]] = None
    ) -> AIResponse[T]:
        start = time.perf_counter()
        ctx = context or {}
        text = ctx.get("text", prompt)

        # Heuristic entity extraction
        entities: List[ExtractedEntity] = []

        # Find potential people
        person_matches = re.findall(r'\b(?:Mr\.|Dr\.|Lord|Sir|President|Governor|Minister)?\s*([A-Z][a-z]+ [A-Z][a-z]+)\b', text)
        for p in set(person_matches[:5]):
            entities.append(ExtractedEntity(name=p, entity_type="PERSON", confidence=0.88))

        # Find potential organizations
        org_matches = re.findall(r'\b([A-Z][a-zA-Z]+ (?:University|Commission|Committee|Department|Congress|Assembly|Institute|Society))\b', text)
        for org in set(org_matches[:4]):
            entities.append(ExtractedEntity(name=org, entity_type="ORGANIZATION", confidence=0.92))

        # Find potential locations
        loc_matches = re.findall(r'\b(India|Maharashtra|Pune|Bombay|London|Delhi|Bengal|Calcutta|Madras|United Kingdom|America)\b', text)
        for loc in set(loc_matches[:4]):
            entities.append(ExtractedEntity(name=loc, entity_type="LOCATION", confidence=0.95))

        # Find potential dates
        year_matches = re.findall(r'\b(1\d{3}|20\d{2})\b', text)
        for yr in set(year_matches[:3]):
            entities.append(ExtractedEntity(name=yr, entity_type="DATE", confidence=0.98))

        # Determine historical period
        historical_period = "20th Century"
        if year_matches:
            latest_yr = int(max(year_matches))
            if latest_yr < 1900:
                historical_period = "19th Century Colonial Era"
            elif latest_yr <= 1947:
                historical_period = "Pre-Independence Era (1900–1947)"
            elif latest_yr <= 1975:
                historical_period = "Post-Independence Nation Building (1947–1975)"
            else:
                historical_period = "Late 20th Century"

        # Topics
        topics = []
        topic_keywords = {
            "Education": ["education", "school", "university", "college", "literacy", "student", "teacher"],
            "Governance": ["government", "policy", "reform", "commission", "legislature", "law", "act"],
            "Civil Rights": ["rights", "liberty", "equality", "movement", "protest", "freedom"],
            "Economic Development": ["trade", "industry", "agriculture", "revenue", "finance", "economy"],
        }
        for topic, kws in topic_keywords.items():
            if any(kw in text.lower() for kw in kws):
                topics.append(topic)

        if not topics:
            topics = ["Historical Records", "Institutional Knowledge"]

        # Summary
        first_sentences = re.split(r'(?<=[.!?])\s+', text.strip())[:3]
        summary = " ".join(first_sentences) if first_sentences else "Historical document archive record."
        if len(summary) > 300:
            summary = summary[:297] + "..."

        if schema == ExtractedMetadata:
            res_data = ExtractedMetadata(
                summary=summary,
                suggested_title=None,
                historical_period=historical_period,
                topics=topics,
                geographic_references=list(set(loc_matches[:3])),
                confidence=0.90,
            )
        else:
            # Generic dictionary matching schema
            res_data = schema.model_validate({
                "metadata": {
                    "summary": summary,
                    "historical_period": historical_period,
                    "topics": topics,
                    "geographic_references": list(set(loc_matches[:3])),
                    "confidence": 0.90,
                },
                "entities": [e.model_dump() for e in entities],
            })

        latency = (time.perf_counter() - start) * 1000
        words = len(text.split())
        usage = TokenUsage(prompt_tokens=words, completion_tokens=150, total_tokens=words + 150)

        return AIResponse(
            data=res_data,
            usage=usage,
            model_name=self.model_name,
            latency_ms=round(latency, 2),
        )

    async def summarize(self, text: str, max_length: int = 300) -> AIResponse[str]:
        start = time.perf_counter()
        first_sentences = re.split(r'(?<=[.!?])\s+', text.strip())[:3]
        summary = " ".join(first_sentences)
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        latency = (time.perf_counter() - start) * 1000
        words = len(text.split())
        return AIResponse(
            data=summary,
            usage=TokenUsage(prompt_tokens=words, completion_tokens=len(summary.split()), total_tokens=words + len(summary.split())),
            model_name=self.model_name,
            latency_ms=round(latency, 2),
        )
