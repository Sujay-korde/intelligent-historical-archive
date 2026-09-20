import pytest
import httpx
from backend.app.core.exceptions import SourceUnavailableError
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.models.canonical import CanonicalArchiveRecord, SearchPage, SourceRawRecord


# Helper to check if external network is reachable
async def is_external_network_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://www.loc.gov")
            return resp.status_code in [200, 301, 302]
    except Exception:
        return False


@pytest.mark.asyncio
async def test_live_library_of_congress_api_search_and_fetch():
    """
    Live Integration Test against the real Library of Congress API (https://www.loc.gov).
    Demonstrates real search query, real response parsing, and real canonical record creation.
    """
    if not await is_external_network_available():
        pytest.skip("External network unavailable. Skipping live LOC integration test.")

    adapter = LibraryOfCongressAdapter()

    # 1. Real search
    search_page: SearchPage = await adapter.search(query="George Washington", limit=2)
    assert isinstance(search_page, SearchPage)
    assert len(search_page.results) > 0

    first_item = search_page.results[0]
    assert first_item.source == "library_of_congress"
    assert first_item.source_id is not None
    assert len(first_item.title) > 0

    # 2. Real record fetch
    raw_record: SourceRawRecord = await adapter.fetch_record(first_item.source_id)
    assert raw_record.source == "library_of_congress"
    assert raw_record.raw_data is not None

    # 3. Real normalization
    canonical: CanonicalArchiveRecord = adapter.normalize(raw_record)
    assert isinstance(canonical, CanonicalArchiveRecord)
    assert canonical.source == "library_of_congress"
    assert canonical.title is not None
    assert canonical.provenance.adapter_version == "1.0.0"
    assert canonical.provenance.original_source_id == first_item.source_id


@pytest.mark.asyncio
async def test_live_internet_archive_api_search_and_fetch():
    """
    Live Integration Test against the real Internet Archive API (https://archive.org).
    Demonstrates real search query, real response parsing, and real canonical record creation.
    """
    if not await is_external_network_available():
        pytest.skip("External network unavailable. Skipping live Internet Archive integration test.")

    adapter = InternetArchiveAdapter()

    # 1. Real search
    search_page: SearchPage = await adapter.search(query="Declaration of Independence", limit=2)
    assert isinstance(search_page, SearchPage)
    assert len(search_page.results) > 0

    first_item = search_page.results[0]
    assert first_item.source == "internet_archive"
    assert first_item.source_id is not None
    assert len(first_item.title) > 0

    # 2. Real record fetch
    raw_record: SourceRawRecord = await adapter.fetch_record(first_item.source_id)
    assert raw_record.source == "internet_archive"
    assert raw_record.raw_data is not None

    # 3. Real normalization
    canonical: CanonicalArchiveRecord = adapter.normalize(raw_record)
    assert isinstance(canonical, CanonicalArchiveRecord)
    assert canonical.source == "internet_archive"
    assert canonical.title is not None
    assert canonical.provenance.adapter_version == "1.0.0"
    assert canonical.provenance.original_source_id == first_item.source_id
