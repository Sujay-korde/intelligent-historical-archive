from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PageInfo(BaseModel):
    """Information and extracted text for an individual page or segment."""
    page_number: int
    text: str
    char_count: int = 0
    word_count: int = 0
    has_images: bool = False
    ocr_applied: bool = False
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRExtractionResult(BaseModel):
    """Result from an OCR provider for an image or page."""
    text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    engine_name: str
    language: str = "eng"
    ocr_applied: bool = True
    warnings: List[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    """
    Standardized, structured result produced by any document processor.
    Decoupled from database mutations.
    """
    extracted_text: str = Field(description="Full normalized text across all pages/segments.")
    pages: List[PageInfo] = Field(default_factory=list, description="Page-by-page extracted content and metadata.")
    total_pages: int = Field(default=0, ge=0)
    ocr_used: bool = Field(default=False, description="Whether OCR was required and applied.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Technical and bibliographic metadata discovered inside the file.")
    processing_warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings encountered during processing.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence score.")
    processor_name: str = Field(description="Name of the processor that executed this extraction.")
    processor_version: str = Field(description="Version of the processor.")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Processing duration in milliseconds.")
    detected_language: Optional[str] = Field(default="English", description="Detected or default language of extracted text.")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when processing concluded.")
