import asyncio
import json
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from backend.app.core.database import async_session_factory
from backend.app.api.deps import get_processing_service, get_storage_provider, get_llm_provider, get_embedding_provider, get_job_manager

sys.stdout.reconfigure(encoding='utf-8')

DOC_ID = uuid.UUID("d9dd339a-0bdf-469d-9a7e-305f09b92731")

async def fix():
    async with async_session_factory() as session:
        print("1. Updating media asset for Rajiv Gandhi record to real MP4 video...")
        await session.execute(text("""
            UPDATE document_media_assets
            SET media_type = 'video',
                mime_type = 'video/mp4',
                storage_key = 'https://archive.org/download/Rajiv.Gandhi.A-04.23/A-04.23.mp4',
                file_size_bytes = 16253212
            WHERE document_id = :doc_id;
        """), {"doc_id": DOC_ID})

        print("2. Enhancing description and subjects for rich archival context...")
        enhanced_desc = (
            "Historical motion picture newsreel recording the official state visit of Prime Minister of Thailand "
            "General Prem Tinsulanonda to New Delhi on March 22, 1985, holding bilateral diplomatic discussions with "
            "Prime Minister Rajiv Gandhi. Preserved in the Rajiv Gandhi Archive Film Collection (Reel A-004), "
            "documenting India-Thailand diplomatic relations, regional cooperation, and South Asian geopolitics."
        )
        await session.execute(text("""
            UPDATE documents
            SET description = :desc,
                record_type = 'video'
            WHERE id = :doc_id;
        """), {"doc_id": DOC_ID, "desc": enhanced_desc})

        await session.execute(text("""
            UPDATE document_metadata
            SET subjects = '["Diplomacy & Foreign Relations", "India-Thailand Relations", "State Visits", "South Asian Geopolitics", "Rajiv Gandhi Era"]'::jsonb,
                locations = '["New Delhi, India", "Thailand"]'::jsonb
            WHERE document_id = :doc_id;
        """), {"doc_id": DOC_ID})

        print("2b. Clearing previous stale chunks and entity mappings for clean reprocessing...")
        await session.execute(text("""
            DELETE FROM chunk_embeddings WHERE chunk_id IN (
                SELECT id FROM document_chunks WHERE document_id = :doc_id
            );
        """), {"doc_id": DOC_ID})
        await session.execute(text("""
            DELETE FROM document_chunks WHERE document_id = :doc_id;
        """), {"doc_id": DOC_ID})
        await session.execute(text("""
            DELETE FROM document_entities WHERE document_id = :doc_id;
        """), {"doc_id": DOC_ID})

        await session.commit()
        print("Updated document, metadata, media asset, and cleared old chunks.")

    print("\n3. Re-running Processing Pipeline (Text extraction, Gemini AI enrichment, pgvector 768d embeddings, graph links)...")
    async with async_session_factory() as proc_session:
        storage = get_storage_provider()
        llm = get_llm_provider()
        embedding = get_embedding_provider()
        job_mgr = get_job_manager()

        from backend.app.services.processing_service import ProcessingService
        proc = ProcessingService(
            session=proc_session,
            storage_provider=storage,
            llm_provider=llm,
            embedding_provider=embedding,
            job_manager=job_mgr,
        )

        await proc.process_document(DOC_ID)
        await proc_session.commit()
        print("Processing pipeline completed successfully!")

    print("\n4. Verifying new state in database:")
    async with async_session_factory() as verify_session:
        d = (await verify_session.execute(text("""
            SELECT d.id, d.title, d.record_type, d.status, d.processing_stage, d.quality_score,
                   (SELECT count(*) FROM document_chunks WHERE document_id = d.id) as chunks_count,
                   (SELECT count(*) FROM document_entities WHERE document_id = d.id) as entities_count
            FROM documents d
            WHERE d.id = :doc_id;
        """), {"doc_id": DOC_ID})).first()
        print(f"  Title: {d.title}")
        print(f"  Record Type: {d.record_type}")
        print(f"  Status: {d.status}")
        print(f"  Processing Stage: {d.processing_stage}")
        print(f"  Quality Score: {d.quality_score}")
        print(f"  Chunks Count: {d.chunks_count}")
        print(f"  Entities Count: {d.entities_count}")

        assets = (await verify_session.execute(text("""
            SELECT media_type, mime_type, storage_key, file_size_bytes
            FROM document_media_assets
            WHERE document_id = :doc_id;
        """), {"doc_id": DOC_ID})).fetchall()
        for a in assets:
            print(f"  Asset: media_type={a.media_type}, mime={a.mime_type}, key={a.storage_key}, size={a.file_size_bytes}")

        entities = (await verify_session.execute(text("""
            SELECT e.name, e.entity_type
            FROM document_entities de
            JOIN entities e ON e.id = de.entity_id
            WHERE de.document_id = :doc_id;
        """), {"doc_id": DOC_ID})).fetchall()
        print(f"  Entities ({len(entities)}):", [f"{e.name} ({e.entity_type})" for e in entities])

        rels = (await verify_session.execute(text("""
            SELECT r.relationship_type, s.name as source_name, t.name as target_name
            FROM relationships r
            JOIN entities s ON s.id = r.source_entity_id
            JOIN entities t ON t.id = r.target_entity_id
            JOIN document_entities de ON (de.entity_id = s.id OR de.entity_id = t.id)
            WHERE de.document_id = :doc_id;
        """), {"doc_id": DOC_ID})).fetchall()
        print(f"  Connections ({len(rels)}):", [f"{r.source_name} -[{r.relationship_type}]-> {r.target_name}" for r in rels])

if __name__ == "__main__":
    asyncio.run(fix())
