from abc import ABC, abstractmethod
from processing.models.result import OCRExtractionResult


class BaseOCRProvider(ABC):
    """
    Abstract interface for Optical Character Recognition providers.
    """
    provider_name: str = "BaseOCRProvider"
    provider_version: str = "1.0.0"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR engine/binary is installed and available."""
        pass

    @abstractmethod
    async def extract_text(self, image_bytes: bytes, language: str = "eng", **kwargs) -> OCRExtractionResult:
        """Extract text and confidence information from raw image bytes."""
        pass

    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Backwards-compatibility helper."""
        res = await self.extract_text(image_bytes)
        return res.text
