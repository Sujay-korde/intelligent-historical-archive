import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import ExifTags, Image

from processing.base import BaseProcessor, ExtractedContent, ExtractedPage
from processing.models.result import PageInfo, ProcessingResult
from processing.ocr.base import BaseOCRProvider
from processing.ocr.tesseract_provider import TesseractOCRProvider
from processing.utils.file_validator import FileValidationError
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """
    Modality processor for archival images, photographs, and scanned plates.
    Performs:
    1. Validation (file existence, non-empty, image magic bytes)
    2. Image format & EXIF metadata inspection via Pillow
    3. Optical Character Recognition via OCRProvider
    4. Text normalization (Unicode NFKC, ligatures, dehyphenation)
    5. Structured ProcessingResult generation
    """
    processor_name: str = "ImageProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = [
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
        "image/bmp",
        "image/gif",
    ]
    supported_extensions: List[str] = [
        "jpg",
        "jpeg",
        "png",
        "tif",
        "tiff",
        "webp",
        "bmp",
        "gif",
    ]

    def __init__(self, ocr_provider: Optional[BaseOCRProvider] = None):
        self.ocr_provider = ocr_provider if ocr_provider is not None else TesseractOCRProvider()

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        if extension and extension.lower().lstrip(".") in self.supported_extensions:
            return True
        if mime_type and any(m in mime_type.lower() for m in ["image"]):
            return True
        return False

    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        start_time = time.perf_counter()
        validated_path = self.validate(Path(file_path))

        warnings: List[str] = []
        discovered_metadata: Dict[str, Any] = {}

        # 1. Inspect image properties via Pillow
        try:
            with Image.open(validated_path) as img:
                width, height = img.size
                discovered_metadata["width"] = width
                discovered_metadata["height"] = height
                discovered_metadata["aspect_ratio"] = round(width / max(height, 1), 4)
                discovered_metadata["format"] = img.format
                discovered_metadata["mode"] = img.mode

                if "dpi" in img.info:
                    dpi = img.info["dpi"]
                    discovered_metadata["dpi"] = list(dpi) if isinstance(dpi, tuple) else dpi

                # Extract standard EXIF tags
                exif_data = img.getexif()
                if exif_data:
                    exif_dict: Dict[str, Any] = {}
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if isinstance(value, (str, int, float)):
                            exif_dict[tag_name] = value
                    if exif_dict:
                        discovered_metadata["exif"] = exif_dict

        except Exception as e:
            raise FileValidationError(f"Invalid or corrupted image file: {e}") from e

        # 2. Extract text via OCR
        raw_bytes = validated_path.read_bytes()
        ocr_applied = False
        raw_text = ""
        ocr_confidence = 0.0

        if self.ocr_provider:
            try:
                ocr_result = await self.ocr_provider.extract_text(raw_bytes)
                raw_text = ocr_result.text
                ocr_applied = ocr_result.ocr_applied
                ocr_confidence = ocr_result.confidence
                if ocr_result.warnings:
                    warnings.extend(ocr_result.warnings)
            except Exception as ocr_err:
                warnings.append(f"Image OCR execution error: {ocr_err}")
        else:
            warnings.append("No OCR provider configured for ImageProcessor.")

        # 3. Normalize text
        normalized_text = normalize_archival_text(raw_text)
        char_count = len(normalized_text)
        word_count = len(normalized_text.split()) if normalized_text else 0

        # Build PageInfo for image (1 visual page)
        page_info = PageInfo(
            page_number=1,
            text=normalized_text,
            char_count=char_count,
            word_count=word_count,
            has_images=True,
            ocr_applied=ocr_applied,
            confidence=ocr_confidence if ocr_applied else 1.0,
            metadata={
                "width": discovered_metadata.get("width"),
                "height": discovered_metadata.get("height"),
                "format": discovered_metadata.get("format"),
            },
        )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingResult(
            extracted_text=normalized_text,
            pages=[page_info],
            total_pages=1,
            ocr_used=ocr_applied,
            metadata=discovered_metadata,
            processing_warnings=warnings,
            confidence=round(ocr_confidence if ocr_applied else 1.0, 4),
            processor_name=self.processor_name,
            processor_version=self.processor_version,
            execution_time_ms=round(execution_time_ms, 2),
            detected_language="English",
        )

    # Backwards compatibility method
    async def extract_content(self, file_path: Path) -> ExtractedContent:
        result = await self.process(file_path)
        return ExtractedContent(
            pages=[
                ExtractedPage(
                    page_number=1,
                    text=result.extracted_text,
                    has_images=True,
                    ocr_applied=result.ocr_used,
                )
            ],
            total_pages=1,
            full_text=result.extracted_text,
            detected_language=result.detected_language,
        )
