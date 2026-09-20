import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.app.models.chunk import DocumentChunk
from backend.app.models.document import Document
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from processing.models.result import ProcessingResult
from processing.ocr.mock_provider import MockOCRProvider
from processing.processors.image_processor import ImageProcessor
from processing.processors.pdf_processor import PDFProcessor
from processing.processors.text_processor import TextProcessor
from processing.registry import ProcessorRegistry, get_default_registry
from processing.services.document_processing_service import DocumentProcessingService
from storage.local_storage import LocalStorageProvider


DATA_DIR = Path("storage/data")
PDF_PATH = DATA_DIR / "documents" / "internet_archive" / "warforunion00beec.pdf"
MANUSCRIPT_PATH = DATA_DIR / "manuscripts" / "internet_archive" / "lettertodeargarr00john_86.pdf"
IMAGE_PATH = DATA_DIR / "images" / "internet_archive" / "arkivkopia.se-ublu-17936.jpg"
TEXT_PATH = DATA_DIR / "documents" / "internet_archive" / "thelifeandpublic22681gut.txt"


# --- 1. Real File Processing Tests ---

@pytest.mark.asyncio
async def test_real_prototype_pdf_processing():
    assert PDF_PATH.exists(), f"Real test asset missing: {PDF_PATH}"

    processor = PDFProcessor()
    result = await processor.process(PDF_PATH)

    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "PDFProcessor"
    assert result.total_pages > 20
    assert len(result.pages) == result.total_pages
    # Check for historical keywords from Henry Ward Beecher's speech
    assert any("union" in p.text.lower() for p in result.pages)
    assert result.confidence > 0.8
    assert result.execution_time_ms > 0


@pytest.mark.asyncio
async def test_real_prototype_manuscript_pdf_processing():
    assert MANUSCRIPT_PATH.exists(), f"Real test asset missing: {MANUSCRIPT_PATH}"

    mock_ocr = MockOCRProvider(mock_text="Scanned letter to William Lloyd Garrison", confidence=0.91)
    processor = PDFProcessor(ocr_provider=mock_ocr)
    result = await processor.process(MANUSCRIPT_PATH)

    assert result.total_pages > 0
    assert len(result.pages) == result.total_pages
    assert result.processor_name == "PDFProcessor"


@pytest.mark.asyncio
async def test_real_prototype_image_processing():
    assert IMAGE_PATH.exists(), f"Real test asset missing: {IMAGE_PATH}"

    mock_ocr = MockOCRProvider(mock_text="Archival Plate - Stockholm Historical Print", confidence=0.95)
    processor = ImageProcessor(ocr_provider=mock_ocr)
    result = await processor.process(IMAGE_PATH)

    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "ImageProcessor"
    assert result.total_pages == 1
    # Verify discovered real image metadata
    assert result.metadata["width"] == 3000
    assert result.metadata["height"] > 0
    assert result.metadata["format"] == "JPEG"
    assert result.ocr_used is True
    assert "Stockholm Historical Print" in result.extracted_text


@pytest.mark.asyncio
async def test_real_prototype_text_processing():
    assert TEXT_PATH.exists(), f"Real test asset missing: {TEXT_PATH}"

    processor = TextProcessor()
    result = await processor.process(TEXT_PATH)

    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "TextProcessor"
    assert result.total_pages == 1
    assert result.metadata["line_count"] > 1000
    assert result.metadata["word_count"] > 5000
    assert len(result.extracted_text) > 10000


# --- 2. Full Orchestration & Database Persistence Linking Tests ---

@pytest.mark.asyncio
async def test_document_processing_service_full_orchestration():
    assert PDF_PATH.exists()

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source="internet_archive",
        source_id="warforunion00beec",
        title="War for the Union",
        description="Historical oration by Henry Ward Beecher",
        record_type="document",
        status="INGESTED",
        processing_stage="INITIAL",
    )

    asset = DocumentMediaAsset(
        id=uuid.uuid4(),
        document_id=doc_id,
        asset_role="primary",
        media_type="document",
        mime_type="application/pdf",
        storage_key=str(PDF_PATH.relative_to("storage/data")).replace("\\", "/"),
    )
    doc.media_assets = [asset]

    meta = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc_id,
        creators=[{"name": "Henry Ward Beecher", "role": "Author"}],
        language="English",
        subjects=["Civil War", "Speeches"],
        raw_metadata={},
        provenance=[],
    )
    doc.doc_metadata = meta

    added_chunks = []

    # Mock AsyncSession
    mock_session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        # If querying Document
        stmt_str = str(stmt)
        if "documents" in stmt_str.lower() and "document_chunks" not in stmt_str.lower() and "document_metadata" not in stmt_str.lower():
            mock_result.scalar_one_or_none.return_value = doc
        elif "document_metadata" in stmt_str.lower():
            mock_result.scalar_one_or_none.return_value = meta
        elif "document_chunks" in stmt_str.lower():
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    def mock_add(entity):
        if isinstance(entity, DocumentChunk):
            added_chunks.append(entity)

    mock_session.execute.side_effect = mock_execute
    mock_session.add = MagicMock(side_effect=mock_add)
    mock_session.delete = MagicMock()
    mock_session.commit = AsyncMock()

    storage_provider = LocalStorageProvider(base_dir=str(DATA_DIR))
    registry = get_default_registry()

    service = DocumentProcessingService(
        session=mock_session,
        storage_provider=storage_provider,
        registry=registry,
    )

    # Run full service processing
    result = await service.process_document(doc_id)

    # Assertions
    assert isinstance(result, ProcessingResult)
    assert result.processor_name == "PDFProcessor"

    # Verify document status updated
    assert doc.status == "PROCESSED"
    assert doc.processing_stage == "TEXT_EXTRACTED"

    # Verify chunks created and linked to document_id
    assert len(added_chunks) > 0
    for chunk in added_chunks:
        assert chunk.document_id == doc_id
        assert chunk.content is not None
        assert len(chunk.content) > 0
        assert chunk.page_number is not None

    # Verify chunk indexing is contiguous
    indices = [c.chunk_index for c in added_chunks]
    assert indices == list(range(len(added_chunks)))

    # Verify metadata enhancement
    assert "file_extracted_metadata" in meta.raw_metadata
    assert meta.raw_metadata["file_extracted_metadata"]["total_pages"] == result.total_pages

    # Verify provenance audit trail
    assert len(meta.provenance) == 1
    assert meta.provenance[0]["processor"] == "PDFProcessor"
    assert meta.provenance[0]["step"] == "document_processing"

    # Verify transaction commit
    assert mock_session.commit.called
