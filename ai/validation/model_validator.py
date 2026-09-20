import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from ai.models.enrichment import AIEnrichmentResult, AIEntity, AIMetadata, AISummary, EntityType

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

ENTITY_TYPE_ALIASES = {
    # Person
    "person": EntityType.PERSON,
    "per": EntityType.PERSON,
    "individual": EntityType.PERSON,
    "author": EntityType.PERSON,
    "speaker": EntityType.PERSON,
    "historical figure": EntityType.PERSON,
    # Organization
    "organization": EntityType.ORGANIZATION,
    "org": EntityType.ORGANIZATION,
    "institution": EntityType.ORGANIZATION,
    "government": EntityType.ORGANIZATION,
    "committee": EntityType.ORGANIZATION,
    "society": EntityType.ORGANIZATION,
    "company": EntityType.ORGANIZATION,
    # Location
    "location": EntityType.LOCATION,
    "loc": EntityType.LOCATION,
    "gpe": EntityType.LOCATION,
    "place": EntityType.LOCATION,
    "city": EntityType.LOCATION,
    "country": EntityType.LOCATION,
    "state": EntityType.LOCATION,
    "region": EntityType.LOCATION,
    # Event
    "event": EntityType.EVENT,
    "battle": EntityType.EVENT,
    "war": EntityType.EVENT,
    "revolution": EntityType.EVENT,
    "treaty": EntityType.EVENT,
    "conference": EntityType.EVENT,
    # Date
    "date": EntityType.DATE,
    "year": EntityType.DATE,
    "time": EntityType.DATE,
    "period": EntityType.DATE,
    # Topic
    "topic": EntityType.TOPIC,
    "subject": EntityType.TOPIC,
    "theme": EntityType.TOPIC,
    "category": EntityType.TOPIC,
}


class ModelOutputValidator:
    """
    Validates and sanitizes raw model output to prevent malformed LLM responses
    from corrupting database schemas or breaking pipelines.
    """

    @staticmethod
    def clean_json_markdown(raw_text: str) -> str:
        """
        Extracts clean JSON substring from potential markdown code fences or conversational wrappers.
        """
        if not raw_text:
            return ""

        text = raw_text.strip()

        # Remove markdown code blocks ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()

        # Find first { or [ and last } or ]
        first_brace = text.find("{")
        first_bracket = text.find("[")

        start_idx = -1
        if first_brace != -1 and first_bracket != -1:
            start_idx = min(first_brace, first_bracket)
        elif first_brace != -1:
            start_idx = first_brace
        elif first_bracket != -1:
            start_idx = first_bracket

        last_brace = text.rfind("}")
        last_bracket = text.rfind("]")
        end_idx = max(last_brace, last_bracket)

        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            return text[start_idx : end_idx + 1]

        return text

    @classmethod
    def normalize_entity_type(cls, raw_type: Any) -> EntityType:
        """
        Safely maps any string, enum, or alias to a valid EntityType.
        Defaults to EntityType.TOPIC if unknown.
        """
        if isinstance(raw_type, EntityType):
            return raw_type

        cleaned = str(raw_type).strip().lower()
        if cleaned in ENTITY_TYPE_ALIASES:
            return ENTITY_TYPE_ALIASES[cleaned]

        try:
            return EntityType(str(raw_type).strip().upper())
        except ValueError:
            logger.warning(f"Unknown entity type '{raw_type}', defaulting to 'TOPIC'")
            return EntityType.TOPIC

    @classmethod
    def sanitize_entity(cls, data: Dict[str, Any]) -> Optional[AIEntity]:
        """
        Validates an individual entity dictionary and converts it to AIEntity.
        Returns None if the entity lacks a valid name.
        """
        name = str(data.get("name", "")).strip()
        if not name or len(name) < 2:
            return None

        # Clamp length to DB field constraint (VARCHAR(255))
        name = name[:255]

        entity_type = cls.normalize_entity_type(data.get("entity_type", EntityType.TOPIC))

        raw_conf = data.get("confidence", 1.0)
        try:
            confidence = max(0.0, min(1.0, float(raw_conf)))
        except (ValueError, TypeError):
            confidence = 0.85

        desc = data.get("description")
        if desc:
            desc = str(desc).strip()

        uri = data.get("authority_uri")
        if uri:
            uri = str(uri).strip()[:512]

        return AIEntity(
            name=name,
            entity_type=entity_type,
            description=desc,
            authority_uri=uri,
            confidence=confidence,
        )

    @classmethod
    def sanitize_metadata(cls, data: Dict[str, Any]) -> AIMetadata:
        """
        Validates metadata fields, ensuring non-null types and clamped confidence.
        """
        raw_conf = data.get("confidence", 1.0)
        try:
            confidence = max(0.0, min(1.0, float(raw_conf)))
        except (ValueError, TypeError):
            confidence = 1.0

        def clean_list(val: Any) -> List[str]:
            if isinstance(val, list):
                return [str(x).strip() for x in val if x and str(x).strip()]
            elif isinstance(val, str) and val.strip():
                return [val.strip()]
            return []

        def clean_str(val: Any) -> Optional[str]:
            if val is not None and str(val).strip():
                return str(val).strip()
            return None

        return AIMetadata(
            title=clean_str(data.get("title")),
            creator=clean_str(data.get("creator")),
            date=clean_str(data.get("date")),
            location=clean_str(data.get("location")),
            organization=clean_str(data.get("organization")),
            document_type=clean_str(data.get("document_type")),
            language=clean_str(data.get("language")) or "English",
            subjects=clean_list(data.get("subjects")),
            topics=clean_list(data.get("topics")),
            historical_period=clean_str(data.get("historical_period")),
            confidence=confidence,
        )

    @classmethod
    def parse_and_validate(cls, raw_text: str, schema: Type[T]) -> T:
        """
        Parses raw text into JSON, validates against schema, and returns typed object.
        Raises ValueError if raw text cannot be parsed or validated.
        """
        clean_text = cls.clean_json_markdown(raw_text)
        if not clean_text:
            raise ValueError("Empty or unparsable LLM response text.")

        try:
            parsed = json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON from LLM: {e}") from e

        if schema == AIEnrichmentResult:
            meta_dict = parsed.get("metadata", {})
            sanitized_meta = cls.sanitize_metadata(meta_dict)

            entities_raw = parsed.get("entities", [])
            sanitized_entities = []
            if isinstance(entities_raw, list):
                for ent in entities_raw:
                    if isinstance(ent, dict):
                        e = cls.sanitize_entity(ent)
                        if e:
                            sanitized_entities.append(e)

            summary_obj = None
            summary_raw = parsed.get("summary")
            if isinstance(summary_raw, dict):
                s_text = str(summary_raw.get("summary", "")).strip()
                if s_text:
                    k_pts = summary_raw.get("key_points", [])
                    if not isinstance(k_pts, list):
                        k_pts = []
                    summary_obj = AISummary(
                        summary=s_text,
                        key_points=[str(k).strip() for k in k_pts if k],
                        confidence=float(summary_raw.get("confidence", 1.0)),
                    )
            elif isinstance(summary_raw, str) and summary_raw.strip():
                summary_obj = AISummary(summary=summary_raw.strip(), confidence=1.0)

            return schema(
                metadata=sanitized_meta,
                entities=sanitized_entities,
                summary=summary_obj,
            )

        elif schema == AIMetadata:
            return cls.sanitize_metadata(parsed)

        elif schema == AISummary:
            if isinstance(parsed, dict):
                return AISummary(
                    summary=str(parsed.get("summary", "")).strip(),
                    key_points=[str(k).strip() for k in parsed.get("key_points", []) if k],
                    confidence=float(parsed.get("confidence", 1.0)),
                )
            elif isinstance(parsed, str):
                return AISummary(summary=parsed.strip(), confidence=1.0)

        # Standard Pydantic fallback
        return schema.model_validate(parsed)
