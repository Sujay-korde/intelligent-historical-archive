import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class CandidateMatch(BaseModel):
    """
    Representation of a candidate document match from a single retrieval source (vector or keyword).
    """
    document_id: uuid.UUID
    rank: int = Field(description="1-based rank within the retrieval method")
    score: float = Field(description="Raw retrieval score (e.g. cosine similarity or ts_rank)")
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    content: str = ""
    match_type: str = "semantic"  # "semantic" or "keyword"
    matched_fields: List[str] = Field(default_factory=list)


class BaseRanker(ABC):
    """
    Abstract interface for search result ranking and score fusion.
    Allows testing, evolving, or replacing ranking heuristics (RRF, linear score fusion, cross-encoders)
    without modifying retrieval or repository layers.
    """

    @abstractmethod
    def rank(
        self,
        semantic_candidates: Dict[uuid.UUID, CandidateMatch],
        keyword_candidates: Dict[uuid.UUID, CandidateMatch],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Fuses candidate signals and returns a sorted list of (document_id, fused_score).
        """
        pass
