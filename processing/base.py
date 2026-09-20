from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from processing.models.result import OCRExtractionResult, PageInfo, ProcessingResult
from processing.ocr.base import BaseOCRProvider
from processing.utils.file_validator import validate_file_integrity


class BaseProcessor(ABC):
    """
    Abstract base processor for modality-specific document processors.
    Enforces the required pipeline flow:
    Document -> validation -> content extraction -> OCR if required -> normalized text -> ProcessingResult
    """
    processor_name: str = "BaseProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = []
    supported_extensions: List[str] = []

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        """Check if this processor supports the given MIME type or file extension."""
        if extension:
            ext = extension.lower().lstrip(".")
            if ext in [e.lower().lstrip(".") for e in self.supported_extensions]:
                return True
        if mime_type:
            mt = mime_type.lower()
            for supported in self.supported_mime_types:
                if supported.lower() in mt or mt in supported.lower():
                    return True
        return False

    def validate(self, file_path: Path) -> Path:
        """
        Validate document presence, size, and header signature.
        Raises FileValidationError if invalid.
        """
        ext = file_path.suffix.lstrip(".")
        return validate_file_integrity(file_path, expected_format=ext if ext else None)

    @abstractmethod
    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        """
        Executes the full pipeline:
        validation -> content extraction -> OCR if required -> normalized text -> ProcessingResult
        """
        pass


# Backwards compatibility classes for existing code
class ExtractedPage(BaseModel):
    page_number: int
    text: str
    has_images: bool = False
    ocr_applied: bool = False


class ExtractedContent(BaseModel):
    pages: List[ExtractedPage]
    total_pages: int
    full_text: str
    detected_language: Optional[str] = "English"


DocumentProcessor = BaseProcessor
OCRProvider = BaseOCRProvider

__all__ = [
    "BaseProcessor",
    "BaseOCRProvider",
    "DocumentProcessor",
    "OCRProvider",
    "ExtractedPage",
    "ExtractedContent",
    "ProcessingResult",
    "PageInfo",
    "OCRExtractionResult",
]
