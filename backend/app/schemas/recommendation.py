import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.search import DocumentSummary, PreviewInformation


class RecommendedDocumentItem(BaseModel):
    """
    A single recommended archival document.
    """
    document: DocumentSummary = Field(..., description="Target recommended document summary")
    score: float = Field(..., description="Composite recommendation score in [0.0, 1.0]")
    semantic_similarity: float = Field(default=0.0, description="Dense vector embedding similarity")
    shared_entities: List[str] = Field(default_factory=list, description="Names of knowledge entities shared with target")
    shared_subjects: List[str] = Field(default_factory=list, description="Shared archival subjects")
    shared_historical_period: Optional[str] = Field(default=None, description="Shared historical era if applicable")
    explanation: str = Field(default="", description="Human-readable explanation of recommendation rationale")
    preview: PreviewInformation = Field(default_factory=PreviewInformation, description="Preview media asset information")


class RecommendationResponse(BaseModel):
    """
    Response envelope for related-document recommendations.
    """
    source_document_id: uuid.UUID = Field(..., description="UUID of document for which recommendations were requested")
    total_recommendations: int = Field(default=0, description="Total related documents found")
    recommendations: List[RecommendedDocumentItem] = Field(default_factory=list, description="Ranked list of related documents")
