import json
from pathlib import Path
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import (
    SourceAPIError,
    SourceMediaDownloadError,
    SourceRecordNotFoundError,
    SourceUnavailableError,
)
from backend.app.models.document import Document
from backend.app.models.metadata import DocumentMetadata
from backend.app.models.media_asset import DocumentMediaAsset
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.models.canonical import CanonicalArchiveRecord, SourceRawRecord, SearchPage
from ingestion.services.ingestion_service import CoreIngestionService
from storage.local_storage import LocalStorageProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# FIXTURE LOADERS (SEPARATED TEST ARTIFACTS)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_loc_raw_record():
    with open(FIXTURES_DIR / "loc_sample_record.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_ia_raw_record():
    with open(FIXTURES_DIR / "ia_sample_record.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_loc_raw_search():
    return {
        "results": [
            {
                "id": "item_loc_1787_001",
                "title": ["United States Constitutional Convention Journal 1787"],
                "description": ["Official journal and secret proceedings of the convention."],
                "date": ["1787"],
                "image_url": ["https://tile.loc.gov/image-service/item_loc_1787_001/default.jpg"],
                "resources": [
                    {
                        "files": [
                            [
                                {"url": "https://tile.loc.gov/storage-services/item_loc_1787_001/document.pdf"}
                            ]
                        ]
                    }
                ],
            }
        ],
        "pagination": {"total": 1, "next": None},
    }


@pytest.fixture
def mock_ia_raw_search():
    return {
        "response": {
            "numFound": 1,
            "docs": [
                {
                    "identifier": "constitutionofun00unit",
                    "title": ["The Constitution of the United States of America"],
                    "description": "Historical publication and annotations on the US Constitution.",
                    "creator": ["United States Constitutional Convention"],
                    "date": "1787",
                    "mediatype": "texts",
                }
            ],
        }
    }


# ---------------------------------------------------------------------------
# 1. LIBRARY OF CONGRESS ADAPTER UNIT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_loc_adapter_search_mocked(mock_loc_raw_search):
    adapter = LibraryOfCongressAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_loc_raw_search
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        search_res = await adapter.search(query="constitution", limit=5)
        assert isinstance(search_res, SearchPage)
        assert len(search_res.results) == 1
        item = search_res.results[0]
        assert item.source == "library_of_congress"
        assert item.source_id == "item_loc_1787_001"
        assert "Constitutional Convention" in item.title
        assert item.media_url.endswith(".pdf")


@pytest.mark.asyncio
async def test_loc_adapter_search_network_failure_raises_explicit_error():
    """Verifies that API connection errors are reported loudly without fake fallback data."""
    adapter = LibraryOfCongressAdapter()

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(SourceUnavailableError, match="unreachable"):
            await adapter.search(query="lincoln")


@pytest.mark.asyncio
async def test_loc_adapter_fetch_record_mocked(mock_loc_raw_record):
    adapter = LibraryOfCongressAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_loc_raw_record
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        raw_record = await adapter.fetch_record(source_id="08034567")
        assert isinstance(raw_record, SourceRawRecord)
        assert raw_record.source == "library_of_congress"
        assert raw_record.source_id == "08034567"
        assert "item" in raw_record.raw_data


@pytest.mark.asyncio
async def test_loc_adapter_fetch_record_not_found_raises_error():
    """Verifies that HTTP 404 returns SourceRecordNotFoundError instead of fake data."""
    adapter = LibraryOfCongressAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(SourceRecordNotFoundError, match="not found"):
            await adapter.fetch_record(source_id="non_existent_item_99999")


def test_loc_normalization_and_provenance(mock_loc_raw_record):
    adapter = LibraryOfCongressAdapter()
    raw_record = SourceRawRecord(
        source="library_of_congress",
        source_id="08034567",
        raw_data=mock_loc_raw_record,
        source_url="https://www.loc.gov/item/08034567/",
    )

    canonical = adapter.normalize(raw_record)
    assert isinstance(canonical, CanonicalArchiveRecord)

    # Core metadata preservation
    assert canonical.source == "library_of_congress"
    assert canonical.source_id == "08034567"
    assert canonical.title == "Report on the Subject of Manufactures"
    assert "Foundational economic report" in canonical.description
    assert canonical.creator == "Hamilton, Alexander"
    assert len(canonical.creators) == 2
    assert canonical.creators[0].name == "Hamilton, Alexander"
    assert canonical.date == "1791"
    assert canonical.date_start == "1791-01-01"
    assert canonical.date_end == "1791-12-31"
    assert canonical.location == "Philadelphia, Pennsylvania"
    assert canonical.language == "English"
    assert canonical.record_type == "manuscript"
    assert canonical.media_type == "document"
    assert "Economic Policy" in canonical.subjects
    assert canonical.rights.get("statement") == "Public Domain. No known copyright restrictions."
    assert canonical.source_url == "https://www.loc.gov/item/08034567/"
    assert canonical.media_url == "https://tile.loc.gov/storage-services/08034567/hamilton_manufactures.pdf"
    assert canonical.external_ids.get("call_number") == "HF105.C1 1791"
    assert canonical.external_ids.get("lccn") == "08034567"

    # Provenance metadata preservation
    assert canonical.provenance.adapter_version == "1.0.0"
    assert canonical.provenance.original_source_id == "08034567"
    assert canonical.provenance.original_source_url == "https://www.loc.gov/item/08034567/"
    assert canonical.provenance.imported_at is not None
    assert len(canonical.provenance_records) >= 3


# ---------------------------------------------------------------------------
# 2. INTERNET ARCHIVE ADAPTER UNIT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ia_adapter_search_mocked(mock_ia_raw_search):
    adapter = InternetArchiveAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ia_raw_search
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        search_res = await adapter.search(query="constitution", limit=5)
        assert isinstance(search_res, SearchPage)
        assert len(search_res.results) == 1
        item = search_res.results[0]
        assert item.source == "internet_archive"
        assert item.source_id == "constitutionofun00unit"
        assert "Constitution" in item.title
        assert item.media_url.endswith(".pdf")


@pytest.mark.asyncio
async def test_ia_adapter_search_network_failure_raises_explicit_error():
    """Verifies that API connection errors are reported loudly without fake fallback data."""
    adapter = InternetArchiveAdapter()

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(SourceUnavailableError, match="unreachable"):
            await adapter.search(query="constitution")


@pytest.mark.asyncio
async def test_ia_adapter_fetch_record_mocked(mock_ia_raw_record):
    adapter = InternetArchiveAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ia_raw_record
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        raw_record = await adapter.fetch_record(source_id="constitutionofun00unit")
        assert isinstance(raw_record, SourceRawRecord)
        assert raw_record.source == "internet_archive"
        assert raw_record.source_id == "constitutionofun00unit"
        assert "metadata" in raw_record.raw_data
        assert "files" in raw_record.raw_data


@pytest.mark.asyncio
async def test_ia_adapter_fetch_record_not_found_raises_error():
    """Verifies that missing IA records raise SourceRecordNotFoundError."""
    adapter = InternetArchiveAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # IA returns {} when item does not exist
        mock_get.return_value = mock_response

        with pytest.raises(SourceRecordNotFoundError, match="does not exist"):
            await adapter.fetch_record(source_id="non_existent_ia_doc_12345")


def test_ia_normalization_and_provenance(mock_ia_raw_record):
    adapter = InternetArchiveAdapter()
    raw_record = SourceRawRecord(
        source="internet_archive",
        source_id="constitutionofun00unit",
        raw_data=mock_ia_raw_record,
        source_url="https://archive.org/details/constitutionofun00unit",
    )

    canonical = adapter.normalize(raw_record)
    assert isinstance(canonical, CanonicalArchiveRecord)

    # Core metadata preservation
    assert canonical.source == "internet_archive"
    assert canonical.source_id == "constitutionofun00unit"
    assert canonical.title == "The Constitution of the United States of America: With Notes"
    assert "Official text and commentary" in canonical.description
    assert canonical.creator == "Madison, James; Hamilton, Alexander; Jay, John"
    assert canonical.date == "1787-09-17"
    assert canonical.date_start == "1787-01-01"
    assert canonical.date_end == "1787-12-31"
    assert canonical.location == "Philadelphia, PA, USA"
    assert canonical.language == "English"
    assert canonical.record_type == "book"
    assert canonical.media_type == "document"
    assert "Federal government" in canonical.subjects
    assert canonical.rights.get("statement") == "http://creativecommons.org/publicdomain/mark/1.0/"
    assert canonical.source_url == "https://archive.org/details/constitutionofun00unit"
    assert canonical.media_url == "https://archive.org/download/constitutionofun00unit/constitutionofun00unit.pdf"
    assert canonical.external_ids.get("isbn") == "9780123456789"
    assert canonical.external_ids.get("ark") == "ark:/13960/t00000000"

    # Provenance metadata preservation
    assert canonical.provenance.adapter_version == "1.0.0"
    assert canonical.provenance.original_source_id == "constitutionofun00unit"
    assert canonical.provenance.original_source_url == "https://archive.org/details/constitutionofun00unit"
    assert canonical.provenance.imported_at is not None
    assert len(canonical.provenance_records) >= 3


# ---------------------------------------------------------------------------
# 3. CANONICAL RECORD CROSS-COMPATIBILITY TESTS
# ---------------------------------------------------------------------------

def test_canonical_record_cross_source_compatibility(mock_loc_raw_record, mock_ia_raw_record):
    """Proves both LOC and IA produce structurally identical and compatible CanonicalArchiveRecords."""
    loc_adapter = LibraryOfCongressAdapter()
    ia_adapter = InternetArchiveAdapter()

    loc_canonical = loc_adapter.normalize(
        SourceRawRecord(
            source="library_of_congress",
            source_id="loc_001",
            raw_data=mock_loc_raw_record,
        )
    )
    ia_canonical = ia_adapter.normalize(
        SourceRawRecord(
            source="internet_archive",
            source_id="ia_001",
            raw_data=mock_ia_raw_record,
        )
    )

    # Both objects are instances of CanonicalArchiveRecord
    assert isinstance(loc_canonical, CanonicalArchiveRecord)
    assert isinstance(ia_canonical, CanonicalArchiveRecord)

    # Verify both dictionaries share the exact same schema keys
    loc_dict = loc_canonical.model_dump()
    ia_dict = ia_canonical.model_dump()
    assert set(loc_dict.keys()) == set(ia_dict.keys())

    # Verify provenance contract on both
    for rec in (loc_canonical, ia_canonical):
        assert hasattr(rec.provenance, "imported_at")
        assert hasattr(rec.provenance, "adapter_version")
        assert hasattr(rec.provenance, "original_source_id")
        assert hasattr(rec.provenance, "original_source_url")


# ---------------------------------------------------------------------------
# 4. END-TO-END PIPELINE PROOF: SOURCE → ADAPTER → CANONICAL RECORD → DATABASE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_end_to_end_ingestion_library_of_congress(
    async_test_db: AsyncSession, test_storage: LocalStorageProvider, mock_loc_raw_record
):
    """
    Proves full flow for Library of Congress:
    LOC Source -> Adapter -> Canonical Archive Record -> Database Entity Persistence
    """
    loc_adapter = LibraryOfCongressAdapter()
    service = CoreIngestionService(session=async_test_db, storage_provider=test_storage)

    async def mock_download_stream(media_url: str):
        yield b"%PDF-1.4\nReal binary data for LOC report\n%%EOF"

    with patch.object(loc_adapter, "fetch_record", new_callable=AsyncMock) as mock_fetch, \
         patch.object(loc_adapter, "download_media", side_effect=mock_download_stream):
        
        mock_fetch.return_value = SourceRawRecord(
            source="library_of_congress",
            source_id="loc_hamilton_01",
            raw_data=mock_loc_raw_record,
            source_url="https://www.loc.gov/item/08034567/",
        )

        doc = await service.ingest_from_adapter(adapter=loc_adapter, source_id="loc_hamilton_01")
        await async_test_db.commit()

        assert doc is not None
        assert doc.source == "library_of_congress"
        assert doc.source_id == "loc_hamilton_01"
        assert doc.title == "Report on the Subject of Manufactures"
        assert doc.status == "INGESTED"

        # Verify Database Metadata
        stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc.id)
        meta = (await async_test_db.execute(stmt)).scalar_one_or_none()
        assert meta is not None
        assert meta.language == "English"
        assert meta.date_raw == "1791"
        assert len(meta.creators) == 2
        assert "Tariffs" in meta.subjects

        # Verify Media Assets
        asset_stmt = select(DocumentMediaAsset).where(DocumentMediaAsset.document_id == doc.id)
        assets = (await async_test_db.execute(asset_stmt)).scalars().all()
        assert len(assets) >= 1
        assert assets[0].mime_type == "application/pdf"
        assert assets[0].checksum_sha256 is not None
        assert await test_storage.exists(assets[0].storage_key) is True


@pytest.mark.asyncio
async def test_end_to_end_ingestion_internet_archive(
    async_test_db: AsyncSession, test_storage: LocalStorageProvider, mock_ia_raw_record
):
    """
    Proves full flow for Internet Archive:
    IA Source -> Adapter -> Canonical Archive Record -> Database Entity Persistence
    """
    ia_adapter = InternetArchiveAdapter()
    service = CoreIngestionService(session=async_test_db, storage_provider=test_storage)

    async def mock_download_stream(media_url: str):
        yield b"%PDF-1.4\nReal binary data for Internet Archive Constitution\n%%EOF"

    with patch.object(ia_adapter, "fetch_record", new_callable=AsyncMock) as mock_fetch, \
         patch.object(ia_adapter, "download_media", side_effect=mock_download_stream):
        
        mock_fetch.return_value = SourceRawRecord(
            source="internet_archive",
            source_id="ia_constitution_01",
            raw_data=mock_ia_raw_record,
            source_url="https://archive.org/details/constitutionofun00unit",
        )

        doc = await service.ingest_from_adapter(adapter=ia_adapter, source_id="ia_constitution_01")
        await async_test_db.commit()

        assert doc is not None
        assert doc.source == "internet_archive"
        assert doc.source_id == "ia_constitution_01"
        assert "Constitution of the United States" in doc.title
        assert doc.status == "INGESTED"

        # Verify Database Metadata
        stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc.id)
        meta = (await async_test_db.execute(stmt)).scalar_one_or_none()
        assert meta is not None
        assert meta.language == "English"
        assert meta.date_raw == "1787-09-17"
        assert "Constitutional law" in meta.subjects[0]

        # Verify Media Assets
        asset_stmt = select(DocumentMediaAsset).where(DocumentMediaAsset.document_id == doc.id)
        assets = (await async_test_db.execute(asset_stmt)).scalars().all()
        assert len(assets) >= 1
        assert assets[0].mime_type == "application/pdf"
        assert assets[0].checksum_sha256 is not None
        assert await test_storage.exists(assets[0].storage_key) is True


@pytest.mark.asyncio
async def test_core_pipeline_source_neutrality(
    async_test_db: AsyncSession, test_storage: LocalStorageProvider, mock_loc_raw_record, mock_ia_raw_record
):
    """
    Proves the Core Ingestion Pipeline is completely agnostic to the origin source.
    Both records are ingested via the exact same ingest_canonical_record function without branching.
    """
    loc_adapter = LibraryOfCongressAdapter()
    ia_adapter = InternetArchiveAdapter()
    service = CoreIngestionService(session=async_test_db, storage_provider=test_storage)

    loc_canonical = loc_adapter.normalize(
        SourceRawRecord(source="library_of_congress", source_id="rec_loc_100", raw_data=mock_loc_raw_record)
    )
    ia_canonical = ia_adapter.normalize(
        SourceRawRecord(source="internet_archive", source_id="rec_ia_200", raw_data=mock_ia_raw_record)
    )

    # Ingest both canonical records through the identical pipeline
    doc1 = await service.ingest_canonical_record(loc_canonical)
    doc2 = await service.ingest_canonical_record(ia_canonical)
    await async_test_db.commit()

    # Query all ingested documents from database
    stmt = select(Document).options(selectinload(Document.doc_metadata)).order_by(Document.created_at.asc())
    docs = (await async_test_db.execute(stmt)).scalars().all()

    assert len(docs) == 2
    assert docs[0].source == "library_of_congress"
    assert docs[1].source == "internet_archive"
    assert docs[0].doc_metadata.creators[0]["name"] == "Hamilton, Alexander"
    assert "Madison, James" in docs[1].doc_metadata.creators[0]["name"]
