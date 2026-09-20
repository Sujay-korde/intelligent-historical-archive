import io
from pathlib import Path
import pytest
from PIL import Image
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from processing.base import BaseProcessor
from processing.models.result import ProcessingResult
from processing.ocr.mock_provider import MockOCRProvider
from processing.ocr.tesseract_provider import TesseractOCRProvider
from processing.processors.image_processor import ImageProcessor
from processing.processors.pdf_processor import PDFProcessor
from processing.processors.text_processor import TextProcessor
from processing.registry import ProcessorRegistry, UnsupportedMediaTypeError, get_default_registry
from processing.utils.file_validator import FileValidationError, validate_file_integrity
from processing.utils.text_normalizer import normalize_archival_text


# --- 1. Text Normalizer Tests ---

def test_text_normalizer_ligatures():
    raw_text = "The ﬁrst ﬂight was an eﬃcient and eﬀective œconomic æra."
    normalized = normalize_archival_text(raw_text)
    assert "first" in normalized
    assert "flight" in normalized
    assert "efficient" in normalized
    assert "effective" in normalized
    assert "oeconomic" in normalized
    assert "aera" in normalized


def test_text_normalizer_dehyphenation():
    raw_text = "The American revo-\nlution was a turning point."
    normalized = normalize_archival_text(raw_text)
    assert "revolution" in normalized
    assert "revo-" not in normalized


def test_text_normalizer_control_chars_and_newlines():
    raw_text = "Historical Document\x00\x05\x1b\n\n\n\nPreserved with care.\r\nNext line."
    normalized = normalize_archival_text(raw_text)
    assert "\x00" not in normalized
    assert "\x05" not in normalized
    assert "\r" not in normalized
    assert "Historical Document\n\nPreserved with care.\nNext line." == normalized


# --- 2. File Validator Tests ---

def test_file_validator_valid_file(tmp_path: Path):
    test_file = tmp_path / "valid.txt"
    test_file.write_text("Hello World", encoding="utf-8")
    assert validate_file_integrity(test_file) == test_file


def test_file_validator_missing_file(tmp_path: Path):
    missing_file = tmp_path / "missing.txt"
    with pytest.raises(FileValidationError, match="File not found"):
        validate_file_integrity(missing_file)


def test_file_validator_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    with pytest.raises(FileValidationError, match="File is empty"):
        validate_file_integrity(empty_file)


def test_file_validator_magic_bytes_mismatch(tmp_path: Path):
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("NOT A REAL PDF HEADER", encoding="utf-8")
    with pytest.raises(FileValidationError, match="File header mismatch"):
        validate_file_integrity(fake_pdf, expected_format="pdf")


# --- 3. OCR Provider Tests ---

@pytest.mark.asyncio
async def test_mock_ocr_provider():
    provider = MockOCRProvider(mock_text="Archival Declaration 1776", confidence=0.96)
    assert provider.is_available() is True
    res = await provider.extract_text(b"fake_image_bytes")
    assert res.text == "Archival Declaration 1776"
    assert res.confidence == 0.96
    assert res.ocr_applied is True
    assert len(res.warnings) == 0


@pytest.mark.asyncio
async def test_mock_ocr_provider_unavailable():
    provider = MockOCRProvider(available=False)
    assert provider.is_available() is False
    res = await provider.extract_text(b"fake_image_bytes")
    assert res.text == ""
    assert res.ocr_applied is False
    assert len(res.warnings) > 0


@pytest.mark.asyncio
async def test_tesseract_ocr_provider_graceful_availability():
    provider = TesseractOCRProvider()
    # Regardless of whether tesseract is installed on host, extract_text should not crash
    res = await provider.extract_text(b"fake_image_bytes")
    assert isinstance(res.warnings, list)
    if not provider.is_available():
        assert res.ocr_applied is False
        assert any("not installed" in w for w in res.warnings)


# --- 4. PDFProcessor Tests ---

@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "test_document.pdf"
    doc = fitz.open()
    doc.set_metadata({
        "title": "Historical Address on Liberty",
        "author": "Archivist John Doe",
        "subject": "American History",
    })

    # Page 1: Digital text
    page1 = doc.new_page()
    page1.insert_text((50, 72), "We hold these truths to be self-evident.", fontsize=12)

    # Page 2: Another page of text
    page2 = doc.new_page()
    page2.insert_text((50, 72), "The second page continues the discussion.", fontsize=12)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def image_only_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "scanned_manuscript.pdf"
    doc = fitz.open()
    page = doc.new_page()

    # Create a small in-memory image to insert into page
    img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    page.insert_image(fitz.Rect(50, 50, 200, 200), stream=img_byte_arr.getvalue())

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.mark.asyncio
async def test_pdf_processor_digital_extraction(sample_pdf: Path):
    processor = PDFProcessor()
    assert processor.can_process(mime_type="application/pdf")
    assert processor.can_process(extension="pdf")

    result = await processor.process(sample_pdf)
    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "PDFProcessor"
    assert result.total_pages == 2
    assert len(result.pages) == 2
    assert "We hold these truths" in result.extracted_text
    assert "The second page continues" in result.extracted_text
    assert result.metadata.get("title") == "Historical Address on Liberty"
    assert result.metadata.get("author") == "Archivist John Doe"
    assert result.ocr_used is False
    assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_pdf_processor_conditional_ocr(image_only_pdf: Path):
    mock_ocr = MockOCRProvider(mock_text="Transcribed historical manuscript text", confidence=0.92)
    processor = PDFProcessor(ocr_provider=mock_ocr)

    result = await processor.process(image_only_pdf)
    assert result.total_pages == 1
    assert result.ocr_used is True
    assert "Transcribed historical manuscript text" in result.extracted_text
    assert result.pages[0].ocr_applied is True
    assert result.pages[0].has_images is True


@pytest.mark.asyncio
async def test_pdf_processor_backwards_compatibility(sample_pdf: Path):
    processor = PDFProcessor()
    content = await processor.extract_content(sample_pdf)
    assert content.total_pages == 2
    assert "We hold these truths" in content.full_text


# --- 5. ImageProcessor Tests ---

@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "historical_map.jpg"
    img = Image.new("RGB", (320, 240), color=(240, 230, 200))
    img.save(img_path, format="JPEG", dpi=(300, 300))
    return img_path


@pytest.mark.asyncio
async def test_image_processor_metadata_and_ocr(sample_image: Path):
    mock_ocr = MockOCRProvider(mock_text="Map of Virginia, 1780", confidence=0.94)
    processor = ImageProcessor(ocr_provider=mock_ocr)

    assert processor.can_process(mime_type="image/jpeg")
    assert processor.can_process(extension="jpg")

    result = await processor.process(sample_image)
    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "ImageProcessor"
    assert result.total_pages == 1
    assert result.ocr_used is True
    assert result.extracted_text == "Map of Virginia, 1780"
    assert result.metadata["width"] == 320
    assert result.metadata["height"] == 240
    assert result.metadata["format"] == "JPEG"
    assert result.metadata["aspect_ratio"] == round(320 / 240, 4)
    assert result.confidence == 0.94


@pytest.mark.asyncio
async def test_image_processor_corrupted_image(tmp_path: Path):
    corrupt_file = tmp_path / "broken.jpg"
    corrupt_file.write_bytes(b"\xff\xd8\xff\xe0" + b"GARBAGE_BYTES_NOT_AN_IMAGE" * 10)
    processor = ImageProcessor()
    with pytest.raises(FileValidationError, match="Invalid or corrupted image"):
        await processor.process(corrupt_file)


# --- 6. TextProcessor Tests ---

@pytest.mark.asyncio
async def test_text_processor_utf8(tmp_path: Path):
    text_file = tmp_path / "diary.txt"
    text_file.write_text("Entry 1: Traveled westward.\n\nEntry 2: Reached the river.", encoding="utf-8")

    processor = TextProcessor()
    assert processor.can_process(mime_type="text/plain")
    assert processor.can_process(extension="txt")

    result = await processor.process(text_file)
    assert result.processor_name == "TextProcessor"
    assert result.total_pages == 1
    assert "Traveled westward" in result.extracted_text
    assert result.metadata["line_count"] == 3
    assert result.metadata["word_count"] > 0
    assert result.ocr_used is False


@pytest.mark.asyncio
async def test_text_processor_latin1_encoding(tmp_path: Path):
    latin1_file = tmp_path / "french_correspondence.txt"
    content = "Correspondance officielle du Ministère de la Guerre: café et résumé."
    latin1_file.write_bytes(content.encode("latin-1"))

    processor = TextProcessor()
    result = await processor.process(latin1_file)
    assert "Ministère de la Guerre" in result.extracted_text
    assert "café" in result.extracted_text
    assert result.metadata["encoding"] in ["latin-1", "iso-8859-1", "cp1252"]


# --- 7. ProcessorRegistry Tests ---

def test_registry_dispatch():
    registry = get_default_registry()

    pdf_proc = registry.get_processor(extension="pdf")
    assert isinstance(pdf_proc, PDFProcessor)

    img_proc = registry.get_processor(mime_type="image/jpeg")
    assert isinstance(img_proc, ImageProcessor)

    txt_proc = registry.get_processor(file_path="historical_notes.md")
    assert isinstance(txt_proc, TextProcessor)


def test_registry_unsupported_media():
    registry = ProcessorRegistry()
    with pytest.raises(UnsupportedMediaTypeError, match="No processor registered"):
        registry.get_processor(extension="xyz")


def test_registry_extensibility_for_future_modalities():
    class AudioProcessor(BaseProcessor):
        processor_name = "AudioProcessor"
        processor_version = "1.0.0"
        supported_mime_types = ["audio/mpeg", "audio/wav", "audio/mp4"]
        supported_extensions = ["mp3", "wav", "m4a"]

        async def process(self, file_path: Path, **kwargs) -> ProcessingResult:
            return ProcessingResult(
                extracted_text="Audio transcript",
                processor_name=self.processor_name,
                processor_version=self.processor_version,
            )

    registry = ProcessorRegistry()
    registry.register(PDFProcessor())
    registry.register(AudioProcessor())

    proc = registry.get_processor(mime_type="audio/mpeg")
    assert isinstance(proc, AudioProcessor)
    assert proc.processor_name == "AudioProcessor"
