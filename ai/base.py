from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIResponse(BaseModel, Generic[T]):
    data: T
    usage: TokenUsage = TokenUsage()
    model_name: str
    latency_ms: float = 0.0


class ExtractedMetadata(BaseModel):
    summary: str
    suggested_title: Optional[str] = None
    historical_period: Optional[str] = None
    topics: List[str] = []
    geographic_references: List[str] = []
    confidence: float = 1.0


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str  # PERSON, ORGANIZATION, LOCATION, EVENT, DATE, TOPIC
    description: Optional[str] = None
    authority_uri: Optional[str] = None
    confidence: float = 1.0


class ExtractedEnrichment(BaseModel):
    metadata: ExtractedMetadata
    entities: List[ExtractedEntity] = []


class LLMProvider(ABC):
    @abstractmethod
    async def extract_structured(
        self, prompt: str, schema: Type[T], context: Optional[Dict[str, Any]] = None
    ) -> AIResponse[T]:
        """Extract structured data adhering to a Pydantic schema with token usage tracking."""
        pass

    @abstractmethod
    async def summarize(self, text: str, max_length: int = 300) -> AIResponse[str]:
        """Summarize text with token tracking."""
        pass


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch-embed texts with automatic chunking and truncation."""
        pass

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        results = await self.embed_texts([text])
        return results[0]

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        pass
