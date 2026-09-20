from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    search_type: str = Field(default="hybrid", description="hybrid, semantic, or keyword")
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    source: Optional[str] = None
    record_type: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    entity_name: Optional[str] = None
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    document_id: UUID
    title: str
    source: str
    source_id: str
    date: Optional[str] = None
    record_type: str
    score: float
    semantic_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    snippet: str
    matching_chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    entities: List[str] = []
    source_url: Optional[str] = None
    access_url: Optional[str] = None
    relevance_explanation: str


class SearchResponse(BaseModel):
    query: str
    search_type: str
    total_results: int
    execution_time_ms: float
    results: List[SearchResultItem]
    facets: Dict[str, Any] = {}
