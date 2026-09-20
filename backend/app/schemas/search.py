from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Search request parameters supporting semantic, keyword, and metadata filters.
    """
    query: str = Field(..., min_length=1, description="Search query string")
    search_type: str = Field(default="hybrid", description="Search mode: hybrid, semantic, or keyword")
    limit: int = Field(default=10, ge=1, le=100, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")

    # Metadata filters
    source: Optional[str] = Field(default=None, description="Filter by archival source repository (e.g., loc, internet_archive)")
    record_type: Optional[str] = Field(default=None, description="Filter by media/record type (e.g., document, audio, manuscript, image)")
    date_start: Optional[str] = Field(default=None, description="Lower bound for document date/year")
    date_end: Optional[str] = Field(default=None, description="Upper bound for document date/year")
    creator: Optional[str] = Field(default=None, description="Filter by creator or author name")
    subject: Optional[str] = Field(default=None, description="Filter by archival subject topic")
    historical_period: Optional[str] = Field(default=None, description="Filter by historical period")
    entity_name: Optional[str] = Field(default=None, description="Filter by linked entity name")

    # Modular ranking weights
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for semantic vector score")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for keyword text score")


class DocumentSummary(BaseModel):
    """
    Document summary container for search results.
    """
    id: UUID = Field(..., description="Document UUID")
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(default=None, description="Document description")
    source: str = Field(..., description="Archival source (e.g., loc, internet_archive)")
    source_id: str = Field(..., description="Original ID from archival provider")
    record_type: str = Field(..., description="Format/modality type")
    source_url: Optional[str] = Field(default=None, description="URL to original repository record")
    status: Optional[str] = Field(default=None, description="Processing status")


class PreviewInformation(BaseModel):
    """
    Available media and preview metadata.
    """
    has_media: bool = Field(default=False, description="True if physical media asset exists")
    media_type: Optional[str] = Field(default=None, description="Type: document, image, audio, video")
    mime_type: Optional[str] = Field(default=None, description="MIME format")
    storage_key: Optional[str] = Field(default=None, description="Storage key in archive")
    preview_url: Optional[str] = Field(default=None, description="Thumbnail or preview URL")
    access_url: Optional[str] = Field(default=None, description="Public streaming/download URL")
    page_number: Optional[int] = Field(default=None, description="Matched page number where available")
    file_size_bytes: Optional[int] = Field(default=None, description="Media file size in bytes")


class MatchedEntityItem(BaseModel):
    """
    Extracted knowledge entity matched with document.
    """
    name: str = Field(..., description="Entity name")
    entity_type: Optional[str] = Field(default=None, description="Entity type: PERSON, ORGANIZATION, LOCATION, etc.")
    confidence: Optional[float] = Field(default=None, description="Extraction confidence")


class SearchResultItem(BaseModel):
    """
    Standardized search result item combining signals.
    Contains:
    - document
    - relevance_score
    - matching_snippet
    - matched_metadata
    - source
    - entities
    - available_preview_information
    """
    document: DocumentSummary = Field(..., description="Matched document record")
    relevance_score: float = Field(..., description="Fused relevance score in [0.0, 1.0]")
    matching_snippet: str = Field(..., description="Contextual excerpt centered on matching query terms")
    matched_metadata: Dict[str, Any] = Field(default_factory=dict, description="Matched metadata attributes")
    source: str = Field(..., description="Archival repository source")
    entities: List[MatchedEntityItem] = Field(default_factory=list, description="Knowledge entities related to document")
    available_preview_information: PreviewInformation = Field(
        default_factory=PreviewInformation, description="Preview and media asset information"
    )

    # Ranking provenance & explanation
    relevance_explanation: str = Field(default="", description="Human-readable match explanation")
    semantic_rank: Optional[int] = Field(default=None, description="Rank from vector retrieval")
    keyword_rank: Optional[int] = Field(default=None, description="Rank from keyword retrieval")
    matching_chunk_index: Optional[int] = Field(default=None, description="Index of best matching chunk")
    page_number: Optional[int] = Field(default=None, description="Page number of best matching chunk")

    # Backwards-compatible convenience properties
    @property
    def document_id(self) -> UUID:
        return self.document.id

    @property
    def title(self) -> str:
        return self.document.title

    @property
    def score(self) -> float:
        return self.relevance_score

    @property
    def snippet(self) -> str:
        return self.matching_snippet

    @property
    def source_id(self) -> str:
        return self.document.source_id

    @property
    def record_type(self) -> str:
        return self.document.record_type

    @property
    def source_url(self) -> Optional[str]:
        return self.document.source_url


class SearchResponse(BaseModel):
    """
    Unified search response envelope.
    """
    query: str = Field(..., description="Original user query")
    search_type: str = Field(..., description="Search mode executed")
    total_results: int = Field(..., description="Total matching documents found")
    execution_time_ms: float = Field(..., description="Total query execution latency in ms")
    results: List[SearchResultItem] = Field(default_factory=list, description="Ranked search results")
    facets: Dict[str, Any] = Field(default_factory=dict, description="Metadata distribution facets")
