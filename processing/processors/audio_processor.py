import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from processing.base import BaseProcessor, ExtractedContent, ExtractedPage
from processing.models.result import PageInfo, ProcessingResult
from processing.utils.text_normalizer import normalize_archival_text

logger = logging.getLogger(__name__)


class AudioProcessor(BaseProcessor):
    """
    Modality processor for historical audio recordings (e.g. speeches, oral histories, broadcasts).
    Designed to allow speech-to-text transcription engines (e.g., Whisper, Vosk, Cloud Speech)
    without modifying core ingestion or pipeline code.
    """
    processor_name: str = "AudioProcessor"
    processor_version: str = "1.0.0"
    supported_mime_types: List[str] = [
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/m4a",
        "audio/x-m4a",
        "audio/mp4",
        "audio/ogg",
        "audio/flac",
    ]
    supported_extensions: List[str] = ["mp3", "wav", "m4a", "ogg", "flac"]

    def __init__(self, transcription_provider: Optional[Any] = None):
        self.transcription_provider = transcription_provider

    def can_process(self, mime_type: Optional[str] = None, extension: Optional[str] = None) -> bool:
        if extension and extension.lower().lstrip(".") in self.supported_extensions:
            return True
        if mime_type and any(m in mime_type.lower() for m in ["audio"]):
            return True
        return False

    async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
        start_time = time.perf_counter()
        validated_path = self.validate(Path(file_path))

        warnings: List[str] = []
        file_size = validated_path.stat().st_size
        discovered_metadata: Dict[str, Any] = {
            "format": validated_path.suffix.lstrip(".").lower(),
            "file_size_bytes": file_size,
        }

        # Transcribe audio if a speech-to-text provider is configured
        transcript = ""
        confidence = 0.90
        if self.transcription_provider and hasattr(self.transcription_provider, "transcribe"):
            try:
                transcript = await self.transcription_provider.transcribe(validated_path)
            except Exception as e:
                warnings.append(f"Audio transcription error: {e}")
        else:
            warnings.append(
                "Audio transcription provider not configured; audio asset registered and metadata extracted."
            )

        normalized_text = normalize_archival_text(transcript)
        page_info = PageInfo(
            page_number=1,
            text=normalized_text,
            char_count=len(normalized_text),
            word_count=len(normalized_text.split()) if normalized_text else 0,
            has_images=False,
            ocr_applied=False,
            confidence=confidence if normalized_text else 1.0,
            metadata=discovered_metadata,
        )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingResult(
            extracted_text=normalized_text,
            pages=[page_info],
            total_pages=1,
            ocr_used=False,
            metadata=discovered_metadata,
            processing_warnings=warnings,
            confidence=confidence if normalized_text else 1.0,
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
