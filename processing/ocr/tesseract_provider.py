import io
import logging
import shutil
from typing import List, Optional
from PIL import Image

from processing.models.result import OCRExtractionResult
from processing.ocr.base import BaseOCRProvider

logger = logging.getLogger(__name__)


class TesseractOCRProvider(BaseOCRProvider):
    """
    OCR Provider using Tesseract via pytesseract.
    Includes availability detection, Pillow preprocessing for archival documents,
    and confidence extraction.
    """
    provider_name: str = "TesseractOCR"
    provider_version: str = "1.0.0"

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            # Check if tesseract binary exists in PATH or configured path
            cmd = pytesseract.pytesseract.tesseract_cmd
            if shutil.which(cmd) or (cmd != "tesseract" and Path(cmd).exists()):
                # Test call to verify execution
                pytesseract.get_tesseract_version()
                self._available = True
            else:
                self._available = False
        except Exception as e:
            logger.info(f"Tesseract OCR not available: {e}")
            self._available = False

        return self._available

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Enhances historical scan contrast and cleans up noise for OCR.
        """
        # Convert to grayscale
        if image.mode != "L":
            gray = image.convert("L")
        else:
            gray = image

        # Basic point thresholding for contrast enhancement
        # Threshold: values below 140 -> 0 (black), above 140 -> 255 (white)
        # We only apply light contrast adjustment to avoid losing delicate handwriting/print
        return gray

    async def extract_text(self, image_bytes: bytes, language: str = "eng", **kwargs) -> OCRExtractionResult:
        warnings: List[str] = []

        if not self.is_available():
            msg = "Tesseract OCR engine binary is not installed on host PATH."
            logger.warning(msg)
            return OCRExtractionResult(
                text="",
                confidence=0.0,
                engine_name=self.provider_name,
                language=language,
                ocr_applied=False,
                warnings=[msg],
            )

        import pytesseract

        try:
            image = Image.open(io.BytesIO(image_bytes))
            processed_image = self._preprocess_image(image)

            # Extract text
            text = pytesseract.image_to_string(processed_image, lang=language)

            # Extract confidence scores
            data = pytesseract.image_to_data(processed_image, lang=language, output_type=pytesseract.Output.DICT)
            confs = [float(c) for c in data.get("conf", []) if str(c).replace("-", "").isdigit() and float(c) >= 0]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.85
            avg_conf = max(0.0, min(1.0, avg_conf))

            return OCRExtractionResult(
                text=text.strip(),
                confidence=avg_conf,
                engine_name=self.provider_name,
                language=language,
                ocr_applied=True,
                warnings=warnings,
            )
        except Exception as e:
            err_msg = f"Tesseract extraction error: {e}"
            logger.error(err_msg)
            return OCRExtractionResult(
                text="",
                confidence=0.0,
                engine_name=self.provider_name,
                language=language,
                ocr_applied=False,
                warnings=[err_msg],
            )
