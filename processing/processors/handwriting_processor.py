import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from processing.base import BaseProcessor, ExtractedContent, ExtractedPage
from processing.models.result import PageInfo, ProcessingResult
from processing.ocr.base import BaseOCRProvider
from processing.ocr.tesseract_provider import TesseractOCRProvider
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class HandwritingProcessor(BaseProcessor):
    """
    Modality processor for handwritten manuscripts, letters, field journals, and historical diaries.
    Employs Handwritten Text Recognition (HTR) models or OCR engines configured for handwriting.
    """
    processor_name: str = "HandwritingProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = [
        "application/x-manuscript",
        "image/x-manuscript",
        "image/vnd.handwriting",
    ]
    supported_extensions: List[str] = ["htr", "ms", "manuscript"]

    def __init__(self, htr_provider: Optional[BaseOCRProvider] = None):
        self.htr_provider = htr_provider if htr_provider is not None else TesseractOCRProvider()

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        if extension and extension.lower().lstrip(".") in self.supported_extensions:
            return True
        if mime_type and any(m in mime_type.lower() for m in ["manuscript", "handwriting"]):
            return True
        return False

    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        start_time = time.perf_counter()
        validated_path = self.validate(Path(file_path))

        warnings: List[str] = []
        raw_bytes = validated_path.read_bytes()
        ocr_applied = False
        text = ""
        confidence = 0.85

        if self.htr_provider and self.htr_provider.is_available():
            try:
                ocr_res = await self.htr_provider.extract_text(raw_bytes)
                text = ocr_res.text
                ocr_applied = ocr_res.ocr_applied
                confidence = ocr_res.confidence
                if ocr_res.warnings:
                    warnings.extend(ocr_res.warnings)
            except Exception as e:
                warnings.append(f"HTR processing error: {e}")
        else:
            warnings.append("HTR provider is not available on this host.")

        normalized_text = normalize_archival_text(text)
        page_info = PageInfo(
            page_number=1,
            text=normalized_text,
            char_count=len(normalized_text),
            word_count=len(normalized_text.split()) if normalized_text else 0,
            has_images=True,
            ocr_applied=ocr_applied,
            confidence=confidence,
            metadata={"source_type": "handwritten_manuscript"},
        )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingResult(
            extracted_text=normalized_text,
            pages=[page_info],
            total_pages=1,
            ocr_used=ocr_applied,
            metadata={"is_handwritten": True, "file_size_bytes": len(raw_bytes)},
            processing_warnings=warnings,
            confidence=confidence,
            processor_name=self.processor_name,
            processor_version=self.processor_version,
            execution_time_ms=round(execution_time_ms, 2),
            detected_language="English",
        )

    async def extract_content(self, file_path: Path) -> ExtractedContent:
        res = await self.process(file_path)
        return ExtractedContent(
            pages=[ExtractedPage(page_number=1, text=res.extracted_text)],
            total_pages=1,
            full_text=res.extracted_text,
            detected_language=res.detected_language,
        )
