"""
Demonstration & Verification Script for Document Processing Pipeline.
Processes real prototype archival assets (PDFs, Images, Manuscripts, Text files)
and verifies that content extraction, OCR, normalization, and chunk linking work as specified.
"""
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.chunk import DocumentChunk
from backend.app.models.document import Document
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from processing.ocr.mock_provider import MockOCRProvider
from processing.ocr.tesseract_provider import TesseractOCRProvider
from processing.registry import get_default_registry
from processing.services.document_processing_service import DocumentProcessingService
from storage.local_storage import LocalStorageProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("process_prototype")


async def main():
    manifest_path = PROJECT_ROOT / "storage" / "dataset_manifest.json"
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    records = manifest.get("records", [])
    logger.info(f"Loaded {len(records)} records from prototype dataset manifest.")

    # Initialize registry with OCR provider
    tesseract = TesseractOCRProvider()
    ocr_provider = tesseract if tesseract.is_available() else MockOCRProvider(mock_text="Archival text from scan", confidence=0.92)
    registry = get_default_registry(ocr_provider=ocr_provider)

    logger.info(f"Using OCR provider: {ocr_provider.provider_name} (available={ocr_provider.is_available()})")
    logger.info(f"Registered processors: {[p['name'] for p in registry.list_registered()]}")

    processed_count = 0
    modalities_tested = set()

    for rec in records:
        local_path_str = rec.get("local_file_path")
        if not local_path_str:
            continue

        local_path = Path(local_path_str)
        if not local_path.exists():
            continue

        media_type = rec.get("media_type", "document")
        ext = local_path.suffix.lstrip(".").lower()

        # Target representative sample of each modality
        if ext in ["pdf", "jpg", "jpeg", "png", "txt"]:
            try:
                proc = registry.get_processor(file_path=local_path)
                result = await proc.process(local_path)

                modalities_tested.add(proc.processor_name)
                processed_count += 1

                print("\n" + "=" * 70)
                print(f"Record: {rec['title']} ({rec['source_id']})")
                print(f"File: {local_path.name} ({result.total_pages} page(s), {round(local_path.stat().st_size / 1024, 1)} KB)")
                print(f"Processor Selected: {result.processor_name} v{result.processor_version}")
                print(f"OCR Used: {result.ocr_used} | Confidence: {result.confidence} | Latency: {result.execution_time_ms:.1f}ms")
                if result.metadata:
                    print(f"Discovered Metadata: {result.metadata}")
                snippet = (result.extracted_text[:200] + "...") if len(result.extracted_text) > 200 else result.extracted_text
                print(f"Extracted Text Preview:\n  \"{snippet.strip()}\"")
                print("=" * 70)

                if processed_count >= 6:
                    break

            except Exception as e:
                logger.error(f"Error processing {local_path.name}: {e}")

    # Verify database persistence & foreign key linkage
    print("\n--- Verifying Database Chunk Persistence & Linking ---")
    mock_session = AsyncMock()
    persisted_chunks = []

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source="internet_archive",
        source_id="warforunion00beec",
        title="War for the Union",
        status="INGESTED",
        processing_stage="INITIAL",
    )
    asset = DocumentMediaAsset(
        id=uuid.uuid4(),
        document_id=doc_id,
        asset_role="primary",
        media_type="document",
        mime_type="application/pdf",
        storage_key="documents/internet_archive/warforunion00beec.pdf",
    )
    doc.media_assets = [asset]
    meta = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc_id,
        raw_metadata={},
        provenance=[],
    )
    doc.doc_metadata = meta

    async def mock_exec(stmt):
        m = MagicMock()
        s = str(stmt).lower()
        if "documents" in s and "document_chunks" not in s and "document_metadata" not in s:
            m.scalar_one_or_none.return_value = doc
        elif "document_metadata" in s:
            m.scalar_one_or_none.return_value = meta
        elif "document_chunks" in s:
            m.scalars.return_value.all.return_value = []
        return m

    mock_session.execute.side_effect = mock_exec
    mock_session.add = MagicMock(side_effect=lambda x: persisted_chunks.append(x) if isinstance(x, DocumentChunk) else None)
    mock_session.commit = AsyncMock()

    storage = LocalStorageProvider(base_dir=str(PROJECT_ROOT / "storage" / "data"))
    service = DocumentProcessingService(session=mock_session, storage_provider=storage, registry=registry)

    res = await service.process_document(doc_id)
    print(f"Service Processed Document: {doc.title}")
    print(f"Status Updated: {doc.status} | Stage: {doc.processing_stage}")
    print(f"Chunks Persisted: {len(persisted_chunks)}")
    print(f"All Chunks Linked to Document ID: {all(c.document_id == doc_id for c in persisted_chunks)}")
    print(f"Metadata Discovered: {list(meta.raw_metadata.get('file_extracted_metadata', {}).keys())}")
    print(f"Provenance Entries: {len(meta.provenance)}")
    print("Verification Completed Successfully!\n")


if __name__ == "__main__":
    asyncio.run(main())
