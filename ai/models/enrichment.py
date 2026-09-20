from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DATE = "DATE"
    TOPIC = "TOPIC"


class AIEntity(BaseModel):
    name: str = Field(description="Normalized name of the extracted historical entity.")
    entity_type: EntityType = Field(description="Standardized category of the entity.")
    description: Optional[str] = Field(default=None, description="Historical context or significance.")
    authority_uri: Optional[str] = Field(default=None, description="Linked authority URI (e.g. Wikidata, VIAF, LOC).")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0.")


class AIMetadata(BaseModel):
    title: Optional[str] = Field(default=None, description="Identified or suggested title of the archival item.")
    creator: Optional[str] = Field(default=None, description="Author, speaker, compiler, or originating entity.")
    date: Optional[str] = Field(default=None, description="Estimated or stated date/time period.")
    location: Optional[str] = Field(default=None, description="Primary geographic location or place of publication/origin.")
    organization: Optional[str] = Field(default=None, description="Associated publishing body, archive, or institution.")
    document_type: Optional[str] = Field(default=None, description="Document modality/genre (e.g., Speech, Letter, Map, Treaty).")
    language: Optional[str] = Field(default="English", description="Primary language of the text.")
    subjects: List[str] = Field(default_factory=list, description="Topical cataloging subjects.")
    topics: List[str] = Field(default_factory=list, description="Broader thematic historical domains.")
    historical_period: Optional[str] = Field(default=None, description="Era or historical period (e.g., American Civil War, Victorian Era).")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score.")


class AISummary(BaseModel):
    summary: str = Field(description="Scholarly, archival abstract or summary of the document.")
    key_points: List[str] = Field(default_factory=list, description="Salient historical points extracted from the text.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score.")


class AIEnrichmentResult(BaseModel):
    metadata: AIMetadata
    entities: List[AIEntity] = Field(default_factory=list)
    summary: Optional[AISummary] = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIResponseEnvelope(BaseModel, Generic[T]):
    data: T
    provider: str = Field(description="Identifier of AI service provider (e.g. MockLLM, Gemini, OpenAI).")
    model: str = Field(description="Name of the specific model utilized.")
    model_version: Optional[str] = Field(default=None, description="Model release version if available.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of derivation.")
    provenance: str = Field(default="AI", description="Origin tag, defaults to 'AI'.")
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = Field(default=0.0, ge=0.0)
    raw_output: Optional[str] = Field(default=None, description="Raw model text before parsing.")
