from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ai.models.enrichment import (
    AIEnrichmentResult,
    AIEntity,
    AIMetadata,
    AIResponseEnvelope,
    AISummary,
)


class MetadataExtractor(ABC):
    """
    Interface for extracting archival and bibliographic metadata from document text.
    Fields include: title, creator, date, location, organization, document_type,
    language, subjects, topics, and historical_period.
    """

    @abstractmethod
    async def extract_metadata(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIMetadata]:
        """Extract structured archival metadata from text."""
        pass


class EntityExtractor(ABC):
    """
    Interface for extracting named entities and knowledge concepts from document text.
    Identifies: PERSON, ORGANIZATION, LOCATION, EVENT, DATE, TOPIC.
    """

    @abstractmethod
    async def extract_entities(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[List[AIEntity]]:
        """Extract typed entities from text."""
        pass


class Summarizer(ABC):
    """
    Interface for generating archival document summaries and salient key points.
    """

    @abstractmethod
    async def summarize(
        self, text: str, max_length: int = 300
    ) -> AIResponseEnvelope[AISummary]:
        """Generate concise archival summary and key points."""
        pass


class AIEnrichmentProvider(MetadataExtractor, EntityExtractor, Summarizer, ABC):
    """
    Unified enrichment provider interface combining metadata extraction,
    entity extraction, and summarization.
    Allows business logic to depend on clean interfaces without coupling to specific LLMs.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider service (e.g. 'MockLLM', 'Gemini', 'OpenAI')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the active LLM."""
        pass

    @property
    def model_version(self) -> Optional[str]:
        """Optional version tag of the active model."""
        return None

    @abstractmethod
    async def enrich(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIEnrichmentResult]:
        """
        Execute full enrichment (metadata, entities, summary) in a single coordinated call.
        """
        pass
