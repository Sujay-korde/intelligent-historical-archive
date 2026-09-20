from typing import Optional
from processing.models.result import OCRExtractionResult
from processing.ocr.base import BaseOCRProvider


class MockOCRProvider(BaseOCRProvider):
    """
    Mock OCR provider for unit tests and offline testing.
    """
    provider_name: str = "MockOCR"
    provider_version: str = "1.0.0"

    def __init__(
        self,
        mock_text: str = "Historical archival text detected from image scan.",
        confidence: float = 0.95,
        available: bool = True,
    ):
        self.mock_text = mock_text
        self.confidence = confidence
        self._available = available

    def is_available(self) -> bool:
        return self._available

    async def extract_text(self, image_bytes: bytes, language: str = "eng", **kwargs) -> OCRExtractionResult:
        if not self._available:
            return OCRExtractionResult(
                text="",
                confidence=0.0,
                engine_name=self.provider_name,
                language=language,
                ocr_applied=False,
                warnings=["Mock OCR is disabled"],
            )

        return OCRExtractionResult(
            text=self.mock_text,
            confidence=self.confidence,
            engine_name=self.provider_name,
            language=language,
            ocr_applied=True,
            warnings=[],
        )
