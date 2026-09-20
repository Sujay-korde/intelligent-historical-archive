import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from processing.base import BaseProcessor, ExtractedContent, ExtractedPage
from processing.models.result import PageInfo, ProcessingResult
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class TextProcessor(BaseProcessor):
    """
    Modality processor for plain text, Markdown, CSV, TSV, and JSON documents.
    Performs:
    1. Validation (existence, non-empty)
    2. Multi-encoding reading (UTF-8, Latin-1, CP1252, ASCII)
    3. Structural analysis (line count, word count, character count)
    4. Text normalization (Unicode NFKC, ligatures, dehyphenation)
    5. Structured ProcessingResult generation
    """
    processor_name: str = "TextProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = [
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "text/tab-separated-values",
    ]
    supported_extensions: List[str] = ["txt", "md", "csv", "json", "tsv"]

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        if extension and extension.lower().lstrip(".") in self.supported_extensions:
            return True
        if mime_type and any(m in mime_type.lower() for m in ["text", "json", "csv"]):
            return True
        return False

    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        start_time = time.perf_counter()
        validated_path = self.validate(Path(file_path))

        raw_bytes = validated_path.read_bytes()
        detected_encoding = "utf-8"
        content = ""

        # Try multiple encodings common in historical text archives
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                content = raw_bytes.decode(enc)
                detected_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        if not content and raw_bytes:
            content = raw_bytes.decode("utf-8", errors="replace")
            detected_encoding = "utf-8-replace"

        # Calculate pre-normalization stats
        raw_lines = content.splitlines()
        line_count = len(raw_lines)

        # Normalize text
        normalized_text = normalize_archival_text(content)
        char_count = len(normalized_text)
        word_count = len(normalized_text.split()) if normalized_text else 0

        discovered_metadata: Dict[str, Any] = {
            "encoding": detected_encoding,
            "line_count": line_count,
            "word_count": word_count,
            "char_count": char_count,
            "file_size_bytes": len(raw_bytes),
        }

        page_info = PageInfo(
            page_number=1,
            text=normalized_text,
            char_count=char_count,
            word_count=word_count,
            has_images=False,
            ocr_applied=False,
            confidence=1.0,
            metadata={"line_count": line_count},
        )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingResult(
            extracted_text=normalized_text,
            pages=[page_info],
            total_pages=1,
            ocr_used=False,
            metadata=discovered_metadata,
            processing_warnings=[],
            confidence=1.0,
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
                    has_images=False,
                    ocr_applied=False,
                )
            ],
            total_pages=1,
            full_text=result.extracted_text,
            detected_language=result.detected_language,
        )
