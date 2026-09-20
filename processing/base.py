from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


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


class DocumentProcessor(ABC):
    @abstractmethod
    def can_process(self, mime_type: str, extension: str) -> bool:
        """Check if this processor supports the given MIME type or file extension."""
        pass

    @abstractmethod
    async def extract_content(self, file_path: Path) -> ExtractedContent:
        """Extract pages and text from document file."""
        pass


class OCRProvider(ABC):
    @abstractmethod
    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes."""
        pass
