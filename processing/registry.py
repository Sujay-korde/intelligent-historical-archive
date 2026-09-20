import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from processing.base import BaseProcessor
from processing.ocr.base import BaseOCRProvider
from processing.processors.image_processor import ImageProcessor
from processing.processors.pdf_processor import PDFProcessor
from processing.processors.text_processor import TextProcessor

logger = logging.getLogger(__name__)


class UnsupportedMediaTypeError(ValueError):
    """Raised when no registered processor can handle the given media type or extension."""
    pass


class ProcessorRegistry:
    """
    Registry for document and media processors.
    Supports dynamic registration of modality processors (PDF, Image, Text, Audio, Video, etc.)
    without modifying core ingestion or pipeline code.
    """

    def __init__(self):
        # List of tuples: (priority, processor)
        self._processors: List[Tuple[int, BaseProcessor]] = []

    def register(self, processor: BaseProcessor, priority: int = 0) -> None:
        """
        Register a processor. Higher priority numbers are evaluated first.
        """
        self._processors.append((priority, processor))
        # Sort descending by priority
        self._processors.sort(key=lambda x: x[0], reverse=True)
        logger.info(
            f"Registered processor '{processor.processor_name}' v{processor.processor_version} "
            f"with priority {priority} for extensions: {processor.supported_extensions}"
        )

    def get_processor(
        self,
        mime_type: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
        extension: Optional[str] = None,
    ) -> BaseProcessor:
        """
        Find and return the appropriate processor for a given MIME type, file path, or extension.
        """
        resolved_ext = extension
        if not resolved_ext and file_path:
            p = Path(file_path)
            resolved_ext = p.suffix.lstrip(".")

        for _, proc in self._processors:
            if proc.can_process(mime_type=mime_type, extension=resolved_ext):
                return proc

        ext_info = f", extension='{resolved_ext}'" if resolved_ext else ""
        mime_info = f", mime_type='{mime_type}'" if mime_type else ""
        raise UnsupportedMediaTypeError(
            f"No processor registered capable of handling file ({mime_info}{ext_info}). "
            f"Registered processors: {[p.processor_name for _, p in self._processors]}"
        )

    def list_registered(self) -> List[Dict[str, Any]]:
        """Return information about all registered processors."""
        return [
            {
                "name": p.processor_name,
                "version": p.processor_version,
                "priority": priority,
                "mime_types": p.supported_mime_types,
                "extensions": p.supported_extensions,
            }
            for priority, p in self._processors
        ]


def get_default_registry(ocr_provider: Optional[BaseOCRProvider] = None) -> ProcessorRegistry:
    """
    Factory creating a ProcessorRegistry pre-loaded with standard processors:
    1. PDFProcessor (priority 10)
    2. ImageProcessor (priority 10)
    3. TextProcessor (priority 5)
    """
    registry = ProcessorRegistry()
    registry.register(PDFProcessor(ocr_provider=ocr_provider), priority=10)
    registry.register(ImageProcessor(ocr_provider=ocr_provider), priority=10)
    registry.register(TextProcessor(), priority=5)
    return registry


# Global default instance
default_registry = get_default_registry()
