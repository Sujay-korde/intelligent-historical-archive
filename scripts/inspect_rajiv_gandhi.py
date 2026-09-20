import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from backend.app.core.database import async_session_factory

sys.stdout.reconfigure(encoding='utf-8')

async def inspect():
    async with async_session_factory() as s:
        res = await s.execute(text("""
            SELECT id, title, record_type, source, source_id, status, processing_stage, quality_score, description
            FROM documents
            WHERE id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        doc = res.first()
        if not doc:
            print("Document d9dd339a-0bdf-469d-9a7e-305f09b92731 NOT FOUND in DB.")
            return

        print("=== DOCUMENT ===")
        for k, v in doc._mapping.items():
            print(f"  {k}: {v}")

        meta = await s.execute(text("""
            SELECT creators, date_raw, language, ai_metadata, provenance
            FROM document_metadata
            WHERE document_id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        m = meta.first()
        print("\n=== METADATA ===")
        if m:
            for k, v in m._mapping.items():
                print(f"  {k}: {v}")

        assets = await s.execute(text("""
            SELECT id, asset_role, media_type, mime_type, storage_key, file_size_bytes, checksum_sha256
            FROM document_media_assets
            WHERE document_id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        print("\n=== MEDIA ASSETS ===")
        asset_list = assets.fetchall()
        for a in asset_list:
            for k, v in a._mapping.items():
                print(f"  {k}: {v}")
            print("  ---")

        chunks = await s.execute(text("""
            SELECT id, chunk_index, length(content) as len, token_count, content
            FROM document_chunks
            WHERE document_id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        print("\n=== CHUNKS ===")
        chunk_list = chunks.fetchall()
        print(f"Total chunks: {len(chunk_list)}")
        for c in chunk_list:
            print(f"  Chunk {c.chunk_index}: {c.len} chars, content: {c.content[:100]}...")

        entities = await s.execute(text("""
            SELECT e.name, e.entity_type, de.confidence
            FROM document_entities de
            JOIN entities e ON e.id = de.entity_id
            WHERE de.document_id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        print("\n=== ENTITIES ===")
        ent_list = entities.fetchall()
        print(f"Total entities: {len(ent_list)}")
        for e in ent_list:
            print(f"  {e.name} ({e.entity_type})")

        # Check graph relationships
        rels = await s.execute(text("""
            SELECT r.relationship_type, s.name as source_name, t.name as target_name
            FROM relationships r
            JOIN entities s ON s.id = r.source_entity_id
            JOIN entities t ON t.id = r.target_entity_id
            JOIN document_entities de ON (de.entity_id = s.id OR de.entity_id = t.id)
            WHERE de.document_id = 'd9dd339a-0bdf-469d-9a7e-305f09b92731';
        """))
        print("\n=== GRAPH CONNECTIONS ===")
        rel_list = rels.fetchall()
        print(f"Total connections: {len(rel_list)}")
        for r in rel_list:
            print(f"  {r.source_name} --[{r.relationship_type}]--> {r.target_name}")

if __name__ == "__main__":
    asyncio.run(inspect())
