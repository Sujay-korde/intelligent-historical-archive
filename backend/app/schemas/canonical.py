from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreatorItem(BaseModel):
    name: str
    role: str = "creator"  # author, editor, photographer, publisher, contributor
    authority_id: Optional[str] = None  # VIAF, LOC authority URI


class MediaAsset(BaseModel):
    asset_id: str
    asset_role: str = "primary"  # primary, thumbnail, transcript, scan_page
    media_type: str  # document, image, audio, video
    mime_type: str
    url: Optional[str] = None
    storage_key: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    page_number: Optional[int] = None


class ProvenanceItem(BaseModel):
    field: str
    value: Any
    source: str  # SOURCE, AI, USER, FILE
    confidence: float = 1.0
    model_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CanonicalArchiveRecord(BaseModel):
    source: str = Field(..., description="External source name: loc, internet_archive, upload")
    source_id: str = Field(..., description="Unique ID within source repository")
    external_ids: Dict[str, str] = Field(default_factory=dict, description="DOI, ARK, Handle, ISBN")
    title: str
    description: Optional[str] = None
    creators: List[CreatorItem] = Field(default_factory=list)
    date_raw: Optional[str] = None
    date_start: Optional[str] = None  # ISO date or YYYY
    date_end: Optional[str] = None    # ISO date or YYYY
    date_is_circa: bool = False
    locations: List[str] = Field(default_factory=list)
    language: Optional[str] = "English"
    record_type: str = Field(default="document", description="manuscript, newspaper, book, report, photograph")
    media_assets: List[MediaAsset] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    rights: Dict[str, Any] = Field(default_factory=dict)
    source_url: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Preserved original source metadata")
    provenance_records: List[ProvenanceItem] = Field(default_factory=list)


class SourceRawRecord(BaseModel):
    source: str
    source_id: str
    raw_data: Dict[str, Any]
    source_url: Optional[str] = None


class SourceSearchResult(BaseModel):
    source: str
    source_id: str
    title: str
    description: Optional[str] = None
    date: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SearchPage(BaseModel):
    results: List[SourceSearchResult]
    next_cursor: Optional[str] = None
    total_count: Optional[int] = None
