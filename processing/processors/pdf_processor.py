import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from processing.base import BaseProcessor, ExtractedContent, ExtractedPage
from processing.models.result import PageInfo, ProcessingResult
from processing.ocr.base import BaseOCRProvider
from processing.ocr.tesseract_provider import TesseractOCRProvider
from processing.utils.file_validator import FileValidationError
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class PDFProcessor(BaseProcessor):
    """
    Modality processor for PDF documents.
    Performs:
    1. Validation (file presence, size, %PDF magic bytes)
    2. Document & metadata extraction via PyMuPDF (fitz)
    3. Conditional OCR for scanned/image pages with low text density (<50 chars)
    4. Text normalization (Unicode NFKC, ligatures, dehyphenation)
    5. Structured ProcessingResult generation
    """
    processor_name: str = "PDFProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = [
        "application/pdf",
        "application/x-pdf",
        "application/acrobat",
        "applications/vnd.pdf",
        "text/pdf",
        "text/x-pdf",
    ]
    supported_extensions: List[str] = ["pdf"]

    def __init__(self, ocr_provider: Optional[BaseOCRProvider] = None):
        self.ocr_provider = ocr_provider if ocr_provider is not None else TesseractOCRProvider()

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        if extension and extension.lower().lstrip(".") in self.supported_extensions:
            return True
        if mime_type and any(m in mime_type.lower() for m in ["pdf"]):
            return True
        return False

    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        start_time = time.perf_counter()
        validated_path = self.validate(Path(file_path))

        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        warnings: List[str] = []
        page_infos: List[PageInfo] = []
        ocr_used = False
        discovered_metadata: Dict[str, Any] = {}

        try:
            doc = fitz.open(str(validated_path))
        except Exception as e:
            raise FileValidationError(f"Corrupt or unreadable PDF: {e}") from e

        try:
            # 1. Discover document metadata
            doc_meta = doc.metadata or {}
            for k, v in doc_meta.items():
                if v and isinstance(v, str) and v.strip():
                    discovered_metadata[k.lower()] = v.strip()
            discovered_metadata["total_pages"] = doc.page_count
            discovered_metadata["is_encrypted"] = doc.is_encrypted

            # 2. Extract page contents
            for page_idx in range(doc.page_count):
                page = doc.load_page(page_idx)
                raw_text = page.get_text("text") or ""
                images = page.get_images()
                has_images = len(images) > 0
                ocr_applied = False
                page_confidence = 0.98

                # Evaluate if page requires OCR
                stripped_len = len(raw_text.strip())
                if stripped_len < 50 and has_images:
                    if self.ocr_provider and self.ocr_provider.is_available():
                        try:
                            # Render page to image at 150 DPI for OCR
                            pix = page.get_pixmap(dpi=150)
                            img_bytes = pix.tobytes("png")
                            ocr_res = await self.ocr_provider.extract_text(img_bytes)
                            if ocr_res.text:
                                raw_text = ocr_res.text
                                ocr_applied = True
                                ocr_used = True
                                page_confidence = ocr_res.confidence
                            if ocr_res.warnings:
                                warnings.extend(ocr_res.warnings)
                        except Exception as ocr_err:
                            warnings.append(f"Page {page_idx + 1} OCR attempt failed: {ocr_err}")
                    else:
                        warnings.append(
                            f"Page {page_idx + 1} has low text density ({stripped_len} chars) "
                            f"and {len(images)} images, but OCR provider is unavailable."
                        )

                # 3. Normalize text
                normalized_text = normalize_archival_text(raw_text)
                char_count = len(normalized_text)
                word_count = len(normalized_text.split()) if normalized_text else 0

                page_infos.append(
                    PageInfo(
                        page_number=page_idx + 1,
                        text=normalized_text,
                        char_count=char_count,
                        word_count=word_count,
                        has_images=has_images,
                        ocr_applied=ocr_applied,
                        confidence=page_confidence,
                        metadata={"image_count": len(images)},
                    )
                )

        finally:
            doc.close()

        # 4. Construct normalized full document text
        full_text_pages = [p.text for p in page_infos if p.text]
        extracted_text = "\n\n".join(full_text_pages)

        # Average confidence
        if page_infos:
            avg_confidence = sum(p.confidence or 1.0 for p in page_infos) / len(page_infos)
        else:
            avg_confidence = 1.0

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingResult(
            extracted_text=extracted_text,
            pages=page_infos,
            total_pages=len(page_infos),
            ocr_used=ocr_used,
            metadata=discovered_metadata,
            processing_warnings=warnings,
            confidence=round(avg_confidence, 4),
            processor_name=self.processor_name,
            processor_version=self.processor_version,
            execution_time_ms=round(execution_time_ms, 2),
            detected_language="English",
        )

    # Backwards compatibility method for earlier pipeline sketches
    async def extract_content(self, file_path: Path) -> ExtractedContent:
        result = await self.process(file_path)
        pages = [
            ExtractedPage(
                page_number=p.page_number,
                text=p.text,
                has_images=p.has_images,
                ocr_applied=p.ocr_applied,
            )
            for p in result.pages
        ]
        return ExtractedContent(
            pages=pages,
            total_pages=result.total_pages,
            full_text=result.extracted_text,
            detected_language=result.detected_language,
        )
