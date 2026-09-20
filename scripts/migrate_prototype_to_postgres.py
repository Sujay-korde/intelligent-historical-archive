import asyncio
import json
import logging
import sqlite3
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

# Ensure repo root is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider
from backend.app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("migration")


def parse_date(date_val):
    if not date_val:
        return None
    try:
        if isinstance(date_val, str):
            clean = date_val.strip()
            if len(clean) == 4 and clean.isdigit():
                return date(int(clean), 1, 1)
            elif len(clean) >= 10:
                return datetime.strptime(clean[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return None


async def migrate():
    sqlite_path = REPO_ROOT / "storage" / "prototype_archive.db"
    if not sqlite_path.exists():
        logger.error(f"SQLite prototype database not found at {sqlite_path}")
        return

    logger.info(f"Connecting to SQLite: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documents;")
    sql_docs = cursor.fetchall()
    logger.info(f"Found {len(sql_docs)} documents in SQLite.")

    cursor.execute("SELECT * FROM document_media_assets;")
    sql_assets = cursor.fetchall()
    assets_by_doc = {}
    for a in sql_assets:
        assets_by_doc.setdefault(a["document_id"], []).append(a)

    cursor.execute("SELECT * FROM document_metadata;")
    sql_meta = cursor.fetchall()
    meta_by_doc = {}
    for m in sql_meta:
        meta_by_doc[m["document_id"]] = m

    logger.info("Connecting to PostgreSQL...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    embedding_provider = None
    if settings.GEMINI_API_KEY:
        try:
            embedding_provider = GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)
            logger.info("Initialized real Gemini dense embedding provider (768d).")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini embeddings: {e}")

    # Track entities for graph linkage: (normalized_name, entity_type) -> UUID
    entity_cache = {}

    async with engine.begin() as pg:
        existing_ents = await pg.execute(text("SELECT id, normalized_name, entity_type FROM entities;"))
        for row in existing_ents:
            entity_cache[(row.normalized_name.lower().strip(), row.entity_type)] = row.id

        migrated_docs = 0
        migrated_assets = 0
        migrated_chunks = 0
        migrated_embeddings = 0
        created_entities = 0
        created_links = 0

        for s_doc in sql_docs:
            raw_id = s_doc["id"]
            try:
                doc_uuid = uuid.UUID(hex=raw_id)
            except ValueError:
                doc_uuid = uuid.UUID(raw_id)

            # Check if document already exists by (source, source_id)
            existing_doc_id = await pg.scalar(
                text("SELECT id FROM documents WHERE source = :source AND source_id = :source_id"),
                {"source": s_doc["source"], "source_id": s_doc["source_id"]},
            )
            if existing_doc_id:
                doc_uuid = existing_doc_id
            else:
                await pg.execute(
                    text("""
                        INSERT INTO documents (
                            id, source, source_id, title, description, record_type, source_url,
                            status, processing_stage, quality_score, created_by, created_at, updated_at
                        ) VALUES (
                            :id, :source, :source_id, :title, :description, :record_type, :source_url,
                            'READY', 'COMPLETED', :quality_score, NULL, NOW(), NOW()
                        )
                    """),
                    {
                        "id": doc_uuid,
                        "source": s_doc["source"],
                        "source_id": s_doc["source_id"],
                        "title": s_doc["title"] or "Untitled Historical Record",
                        "description": s_doc["description"],
                        "record_type": s_doc["record_type"] or "document",
                        "source_url": s_doc["source_url"],
                        "quality_score": float(s_doc["quality_score"] or 1.0),
                    },
                )
                migrated_docs += 1

            # Migrate Media Assets
            doc_assets = assets_by_doc.get(raw_id, [])
            for s_asset in doc_assets:
                try:
                    asset_uuid = uuid.UUID(hex=s_asset["id"])
                except ValueError:
                    asset_uuid = uuid.UUID(s_asset["id"])

                storage_key = s_asset["storage_key"]
                if "storage/data/" in storage_key:
                    storage_key = storage_key.split("storage/data/")[-1]
                storage_key = storage_key.replace("\\", "/").lstrip("/")

                asset_exists = await pg.scalar(
                    text("SELECT count(*) FROM document_media_assets WHERE storage_key = :key OR id = :id"),
                    {"key": storage_key, "id": asset_uuid},
                )
                if asset_exists == 0:
                    await pg.execute(
                        text("""
                            INSERT INTO document_media_assets (
                                id, document_id, asset_role, media_type, mime_type, storage_key,
                                file_size_bytes, checksum_sha256, page_number, created_at
                            ) VALUES (
                                :id, :document_id, :asset_role, :media_type, :mime_type, :storage_key,
                                :file_size_bytes, :checksum_sha256, :page_number, NOW()
                            )
                        """),
                        {
                            "id": asset_uuid,
                            "document_id": doc_uuid,
                            "asset_role": s_asset["asset_role"] or "primary",
                            "media_type": s_asset["media_type"] or "document",
                            "mime_type": s_asset["mime_type"] or "application/octet-stream",
                            "storage_key": storage_key,
                            "file_size_bytes": s_asset["file_size_bytes"],
                            "checksum_sha256": s_asset["checksum_sha256"],
                            "page_number": s_asset["page_number"],
                        },
                    )
                    migrated_assets += 1

            # Migrate Metadata
            s_meta = meta_by_doc.get(raw_id)
            meta_exists = await pg.scalar(
                text("SELECT count(*) FROM document_metadata WHERE document_id = :doc_id"), {"doc_id": doc_uuid}
            )
            parsed_subjects = []
            parsed_locations = []
            parsed_creators = []
            date_raw = None
            date_start_parsed = None

            if s_meta and meta_exists == 0:
                try:
                    meta_uuid = uuid.UUID(hex=s_meta["id"])
                except ValueError:
                    meta_uuid = uuid.UUID(s_meta["id"])

                try:
                    parsed_creators = json.loads(s_meta["creators"]) if s_meta["creators"] else []
                except Exception:
                    parsed_creators = []

                try:
                    parsed_locations = json.loads(s_meta["locations"]) if s_meta["locations"] else []
                except Exception:
                    parsed_locations = []

                try:
                    parsed_subjects = json.loads(s_meta["subjects"]) if s_meta["subjects"] else []
                except Exception:
                    parsed_subjects = []

                date_raw = s_meta["date_raw"]
                date_start_parsed = parse_date(s_meta["date_start"] or date_raw)

                provenance_envelope = [
                    {
                        "model": "gemini-flash-lite-latest",
                        "provider": "Gemini",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "provenance": "AI",
                        "confidence": 0.95,
                    }
                ]

                ai_meta = {
                    "document_type": s_doc["record_type"],
                    "language": s_meta["language"] or "English",
                    "historical_period": "Historical Archive Holding",
                    "confidence": 0.95,
                    "provider": "Gemini",
                }

                await pg.execute(
                    text("""
                        INSERT INTO document_metadata (
                            id, document_id, creators, date_raw, date_start, date_end, date_is_circa,
                            locations, language, organization, subjects, rights, external_ids,
                            raw_metadata, ai_metadata, provenance, confidence, created_at
                        ) VALUES (
                            :id, :document_id, :creators, :date_raw, :date_start, NULL, FALSE,
                            :locations, :language, :organization, :subjects, '{}', '{}',
                            '{}', :ai_metadata, :provenance, 0.95, NOW()
                        )
                    """),
                    {
                        "id": meta_uuid,
                        "document_id": doc_uuid,
                        "creators": json.dumps(parsed_creators),
                        "date_raw": date_raw,
                        "date_start": date_start_parsed,
                        "locations": json.dumps(parsed_locations),
                        "language": s_meta["language"] or "English",
                        "organization": s_meta["organization"] if "organization" in s_meta.keys() else None,
                        "subjects": json.dumps(parsed_subjects),
                        "ai_metadata": json.dumps(ai_meta),
                        "provenance": json.dumps(provenance_envelope),
                    },
                )

            # Create Chunks & Embeddings if missing
            chunk_exists = await pg.scalar(
                text("SELECT count(*) FROM document_chunks WHERE document_id = :doc_id"), {"doc_id": doc_uuid}
            )
            if chunk_exists == 0:
                title = s_doc["title"] or ""
                desc = s_doc["description"] or ""
                subjs = ", ".join(parsed_subjects) if parsed_subjects else ""
                creator_names = ", ".join([c.get("name", "") for c in parsed_creators if isinstance(c, dict)])

                content_parts = [f"Title: {title}"]
                if creator_names:
                    content_parts.append(f"Author / Creator: {creator_names}")
                if date_raw:
                    content_parts.append(f"Date: {date_raw}")
                if subjs:
                    content_parts.append(f"Subjects: {subjs}")
                if desc:
                    content_parts.append(f"Description: {desc}")

                full_content = "\n".join(content_parts)
                chunk_uuid = uuid.uuid4()

                await pg.execute(
                    text("""
                        INSERT INTO document_chunks (
                            id, document_id, chunk_index, content, page_number,
                            token_count, created_at
                        ) VALUES (
                            :id, :document_id, 0, :content, 1,
                            :token_count, NOW()
                        )
                    """),
                    {
                        "id": chunk_uuid,
                        "document_id": doc_uuid,
                        "content": full_content,
                        "token_count": len(full_content.split()),
                    },
                )
                migrated_chunks += 1

                # Generate Gemini dense embedding
                if embedding_provider:
                    try:
                        emb = await embedding_provider.embed_text(full_content[:1500])
                        emb_str = f"[{','.join(f'{x:.6f}' for x in emb)}]"
                        await pg.execute(
                            text("""
                                INSERT INTO chunk_embeddings (
                                    id, chunk_id, model_name, model_version, dimension,
                                    embedding, is_active, created_at
                                ) VALUES (
                                    :id, :chunk_id, 'gemini-embedding-001', '1.0', 768,
                                    CAST(:embedding AS vector), TRUE, NOW()
                                )
                            """),
                            {
                                "id": uuid.uuid4(),
                                "chunk_id": chunk_uuid,
                                "embedding": emb_str,
                            },
                        )
                        migrated_embeddings += 1
                        await asyncio.sleep(0.1)  # small pause for rate limits
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for doc {doc_uuid}: {e}")

            # Entity Extraction & Knowledge Graph Linking
            entities_to_link = []

            # 1. Creators -> PERSON
            for c in parsed_creators:
                c_name = c.get("name") if isinstance(c, dict) else str(c)
                if c_name and len(c_name.strip()) > 2 and c_name.lower().strip() not in ["creator", "author", "unknown"]:
                    entities_to_link.append((c_name.strip(), "PERSON"))

            # 2. Locations -> LOCATION
            for loc in parsed_locations:
                if loc and len(loc.strip()) > 2:
                    entities_to_link.append((loc.strip(), "LOCATION"))

            # 3. Selected Subjects -> EVENT or TOPIC
            for subj in parsed_subjects[:3]:
                if subj and len(subj.strip()) > 2:
                    etype = "EVENT" if any(k in subj.lower() for k in ["war", "revolution", "speech", "treaty", "conference"]) else "TOPIC"
                    entities_to_link.append((subj.strip(), etype))

            seen = set()
            doc_entity_ids = []
            for name, etype in entities_to_link:
                normalized = name.lower().strip()
                key = (normalized, etype)
                if key in seen:
                    continue
                seen.add(key)

                ent_id = entity_cache.get(key)
                if not ent_id:
                    ent_id = uuid.uuid4()
                    await pg.execute(
                        text("""
                            INSERT INTO entities (id, name, normalized_name, entity_type, metadata, created_at)
                            VALUES (:id, :name, :normalized_name, :entity_type, '{}', NOW())
                            ON CONFLICT (entity_type, normalized_name) DO UPDATE SET name = EXCLUDED.name
                            RETURNING id;
                        """),
                        {"id": ent_id, "name": name, "normalized_name": normalized, "entity_type": etype},
                    )
                    entity_cache[key] = ent_id
                    created_entities += 1

                doc_entity_ids.append(ent_id)

                await pg.execute(
                    text("""
                        INSERT INTO document_entities (
                            document_id, entity_id, confidence, provenance, relationship_type
                        ) VALUES (
                            :document_id, :entity_id, 0.95, 'SOURCE', 'MENTIONS'
                        ) ON CONFLICT (document_id, entity_id, relationship_type) DO NOTHING
                    """),
                    {
                        "document_id": doc_uuid,
                        "entity_id": ent_id,
                    },
                )
                created_links += 1

            # Inter-entity relationships
            if len(doc_entity_ids) >= 2:
                primary_actor = doc_entity_ids[0]
                for other_actor in doc_entity_ids[1:4]:
                    await pg.execute(
                        text("""
                            INSERT INTO relationships (
                                id, source_entity_id, target_entity_id, relationship_type,
                                confidence, source_document_id, created_at
                            ) VALUES (
                                :id, :source_id, :target_id, 'ASSOCIATED_WITH',
                                0.90, :doc_id, NOW()
                            )
                        """),
                        {
                            "id": uuid.uuid4(),
                            "source_id": primary_actor,
                            "target_id": other_actor,
                            "doc_id": doc_uuid,
                        },
                    )

        logger.info("=" * 60)
        logger.info("PROTOTYPE MIGRATION COMPLETE")
        logger.info(f"Documents Migrated:       {migrated_docs}")
        logger.info(f"Media Assets Migrated:    {migrated_assets}")
        logger.info(f"Chunks Migrated:          {migrated_chunks}")
        logger.info(f"Embeddings Generated:     {migrated_embeddings}")
        logger.info(f"Entities Created:         {created_entities}")
        logger.info(f"Document Links Created:   {created_links}")
        logger.info("=" * 60)

    conn.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
