from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.canonical import CreatorItem, MediaAsset, ProvenanceItem


class DocumentMetadataResponse(BaseModel):
    creators: List[Any] = []
    date_raw: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    date_is_circa: bool = False
    locations: List[str] = []
    language: Optional[str] = "English"
    organization: Optional[str] = None
    subjects: List[str] = []
    rights: Dict[str, Any] = {}
    external_ids: Dict[str, str] = {}
    raw_metadata: Dict[str, Any] = {}
    ai_metadata: Dict[str, Any] = {}
    provenance: List[Any] = []
    confidence: float = 1.0


class DocumentMediaAssetResponse(BaseModel):
    id: UUID
    asset_role: str
    media_type: str
    mime_type: str
    storage_key: str
    access_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_number: Optional[int] = None


class DocumentSummaryResponse(BaseModel):
    id: UUID
    source: str
    source_id: str
    title: str
    description: Optional[str] = None
    record_type: str
    source_url: Optional[str] = None
    status: str
    processing_stage: str
    quality_score: float = 0.0
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentSummaryResponse):
    metadata: Optional[DocumentMetadataResponse] = None
    media_assets: List[DocumentMediaAssetResponse] = []
    entities_count: int = 0
    chunks_count: int = 0


class DocumentListResponse(BaseModel):
    items: List[DocumentSummaryResponse]
    total: int
    page: int
    page_size: int
