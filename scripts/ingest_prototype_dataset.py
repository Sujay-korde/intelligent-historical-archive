import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is in python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.core.exceptions import (
    SourceAPIError,
    SourceMediaDownloadError,
    SourceRecordNotFoundError,
    SourceUnavailableError,
)
from backend.app.models.document import Document
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter
from ingestion.adapters.loc_adapter import LibraryOfCongressAdapter
from ingestion.models.canonical import CanonicalArchiveRecord, SearchPage, SourceRawRecord
from ingestion.services.ingestion_service import CoreIngestionService
from storage.local_storage import LocalStorageProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("ingestion_runner")

# SQLite fallback compatibility for offline local runs
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


TARGET_QUERIES = [
    # 1. Historical Audio (Speeches, Broadcasts, Recordings)
    {"source": "internet_archive", "query": "title:(speech) AND mediatype:audio AND year:[1890 TO 1960]", "limit": 6},
    {"source": "internet_archive", "query": "collection:(greatest_speeches) AND mediatype:audio", "limit": 4},
    # 2. Historical Images, Cartography & Vintage Photographs
    {"source": "internet_archive", "query": "mediatype:image AND title:(map) AND year:[1750 TO 1900]", "limit": 6},
    {"source": "internet_archive", "query": "mediatype:image AND (\"Civil War\" OR \"photograph\") AND year:[1860 TO 1920]", "limit": 6},
    # 3. Historical Manuscripts, Handwritten Letters & Diaries
    {"source": "internet_archive", "query": "mediatype:texts AND (subject:manuscript OR title:manuscript OR title:diary) AND year:[1700 TO 1900]", "limit": 8},
    {"source": "internet_archive", "query": "collection:(bplscas) AND mediatype:texts", "limit": 6},
    # 4. Founding Documents & Printed Historical Treatises
    {"source": "internet_archive", "query": "title:(Federalist) AND mediatype:texts", "limit": 5},
    {"source": "internet_archive", "query": "title:(Declaration of Independence) AND mediatype:texts", "limit": 4},
    {"source": "internet_archive", "query": "creator:(Abraham Lincoln) AND mediatype:texts", "limit": 5},
    # 5. Direct Library of Congress API Queries (Live upstream error transparency)
    {"source": "library_of_congress", "query": "abraham lincoln", "limit": 2},
    {"source": "library_of_congress", "query": "declaration of independence", "limit": 2},
]


async def run_prototype_ingestion():
    logger.info("Initializing Real Prototype Ingestion Dataset Pipeline...")

    # Initialize Database Session
    db_url = settings.DATABASE_URL
    use_sqlite = False

    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            pass
    except Exception as e:
        logger.warning(f"PostgreSQL connection not reachable ({e}). Using local persistent SQLite store for prototype dataset.")
        use_sqlite = True
        db_path = Path("./storage/prototype_archive.db").resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    storage_provider = LocalStorageProvider(base_dir=settings.STORAGE_LOCAL_DIR)

    loc_adapter = LibraryOfCongressAdapter()
    ia_adapter = InternetArchiveAdapter()

    manifest_entries: List[Dict[str, Any]] = []
    discovered_count = 0
    normalized_count = 0
    stored_count = 0
    failed_count = 0
    failure_reasons: Dict[str, int] = {}

    seen_ids = set()

    async with session_factory() as session:
        service = CoreIngestionService(session=session, storage_provider=storage_provider)

        for q_spec in TARGET_QUERIES:
            source_type = q_spec["source"]
            query = q_spec["query"]
            limit = q_spec["limit"]
            adapter = loc_adapter if source_type == "library_of_congress" else ia_adapter

            logger.info(f"Querying [{source_type}] for: '{query}' (limit={limit})...")

            try:
                search_page: SearchPage = await adapter.search(query=query, limit=limit)
            except Exception as e:
                logger.warning(f"Search failed for [{source_type}] '{query}': {e}")
                err_type = type(e).__name__
                failure_reasons[f"{source_type}:search:{err_type}"] = failure_reasons.get(f"{source_type}:search:{err_type}", 0) + 1
                failed_count += 1
                manifest_entries.append({
                    "source": source_type,
                    "source_id": f"query_{query}",
                    "title": f"Search Query: {query}",
                    "source_url": None,
                    "media_url": None,
                    "media_type": None,
                    "ingestion_status": "FAILED",
                    "failure_reason": f"{err_type}: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                continue

            for search_item in search_page.results:
                discovered_count += 1
                sid = search_item.source_id
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)

                logger.info(f" -> Processing record [{source_type}] ID: {sid} | Title: {search_item.title[:45]}...")

                try:
                    # 1. Fetch raw metadata
                    raw_record: SourceRawRecord = await adapter.fetch_record(sid)

                    # 2. Normalize to CanonicalArchiveRecord
                    canonical: CanonicalArchiveRecord = adapter.normalize(raw_record)
                    normalized_count += 1

                    # 3. Stream & store media assets if available (full intact files under 25MB)
                    local_file_path = None
                    if canonical.media_assets and canonical.media_assets[0].url:
                        primary_asset = canonical.media_assets[0]
                        m_type = canonical.media_type
                        r_type = canonical.record_type
                        
                        # Determine category folder and clean extension
                        if m_type == "audio":
                            folder = "audio"
                            ext = "mp3" if "mpeg" in primary_asset.mime_type or "mp3" in primary_asset.mime_type else "m4a" if "mp4" in primary_asset.mime_type else "ogg" if "ogg" in primary_asset.mime_type else "wav"
                        elif m_type == "image":
                            folder = "images"
                            ext = "png" if "png" in primary_asset.mime_type else "jpg"
                        elif r_type == "manuscript":
                            folder = "manuscripts"
                            ext = "pdf" if "pdf" in primary_asset.mime_type else "jpg" if "image" in primary_asset.mime_type else "txt"
                        else:
                            folder = "documents"
                            ext = "pdf" if "pdf" in primary_asset.mime_type else "txt" if "text" in primary_asset.mime_type else "pdf"

                        storage_key = f"{folder}/{canonical.source}/{canonical.source_id}.{ext}"

                        # Skip files known to be excessively large (> 25MB) to prevent stalls
                        is_too_large = primary_asset.file_size_bytes and primary_asset.file_size_bytes > 25 * 1024 * 1024

                        if not is_too_large:
                            try:
                                media_stream = await adapter.download_media(primary_asset.url)
                                stored_meta = await storage_provider.save_stream(
                                    stream=media_stream,
                                    destination_key=storage_key,
                                    content_type=primary_asset.mime_type,
                                    max_bytes=None,  # Intact complete file - 100% valid structure
                                )
                                primary_asset.storage_key = stored_meta.storage_key
                                primary_asset.file_size_bytes = stored_meta.file_size_bytes
                                primary_asset.checksum_sha256 = stored_meta.checksum_sha256
                                local_file_path = str(storage_provider.get_local_path(stored_meta.storage_key))
                                logger.info(f"    [Media Saved] {stored_meta.file_size_bytes} bytes -> {storage_key}")
                            except Exception as e:
                                logger.info(f"    [Notice] Media download omitted/restricted for {sid}: {e}")
                        else:
                            logger.info(f"    [Notice] Media download skipped for {sid}: file size ({primary_asset.file_size_bytes} bytes) exceeds 25MB threshold.")

                    # 4. Ingest canonical record into database
                    doc: Document = await service.ingest_canonical_record(canonical, auto_process=False)
                    await session.commit()
                    stored_count += 1

                    manifest_entries.append({
                        "source": canonical.source,
                        "source_id": canonical.source_id,
                        "title": canonical.title,
                        "creator": canonical.creator,
                        "date": canonical.date_raw,
                        "location": canonical.location,
                        "language": canonical.language,
                        "record_type": canonical.record_type,
                        "media_type": canonical.media_type,
                        "source_url": canonical.source_url,
                        "media_url": canonical.media_url,
                        "local_file_path": local_file_path,
                        "file_size_bytes": primary_asset.file_size_bytes if canonical.media_assets else None,
                        "subjects": canonical.subjects[:5],
                        "rights": canonical.rights,
                        "ingestion_status": "SUCCESS",
                        "failure_reason": None,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    logger.info(f"    [OK] Ingested successfully: '{canonical.title[:40]}'")

                except Exception as e:
                    await session.rollback()
                    failed_count += 1
                    err_type = type(e).__name__
                    err_msg = str(e)
                    failure_reasons[f"{source_type}:{err_type}"] = failure_reasons.get(f"{source_type}:{err_type}", 0) + 1
                    logger.warning(f"    [FAILED] {sid}: {err_type} - {err_msg}")

                    manifest_entries.append({
                        "source": source_type,
                        "source_id": sid,
                        "title": search_item.title,
                        "source_url": search_item.media_url,
                        "media_url": search_item.media_url,
                        "media_type": search_item.record_type,
                        "ingestion_status": "FAILED",
                        "failure_reason": f"{err_type}: {err_msg}",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                # Polite throttling
                await asyncio.sleep(0.2)

    await engine.dispose()

    # Save manifest
    manifest_path = Path("./storage/dataset_manifest.json").resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_records_discovered": discovered_count,
        "total_records_normalized": normalized_count,
        "total_records_stored": stored_count,
        "total_records_failed": failed_count,
        "failure_breakdown": failure_reasons,
        "records": manifest_entries,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Manifest written to: {manifest_path}")
    print("\n" + "="*70)
    print("PROTOTYPE INGESTION DATASET SUMMARY REPORT")
    print("="*70)
    print(f"Records Discovered:          {discovered_count}")
    print(f"Records Successfully Normalized: {normalized_count}")
    print(f"Records Stored:              {stored_count}")
    print(f"Records Failed:              {failed_count}")
    print("\nFailure Breakdown by Source & Error:")
    for reason, count in failure_reasons.items():
        print(f" - {reason}: {count}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(run_prototype_ingestion())
