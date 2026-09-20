import asyncio
import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings


async def inspect_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.connect() as conn:
            # Counts
            doc_count = await conn.scalar(text("SELECT count(*) FROM documents;"))
            media_count = await conn.scalar(text("SELECT count(*) FROM document_media_assets;"))
            meta_count = await conn.scalar(text("SELECT count(*) FROM document_metadata;"))
            chunk_count = await conn.scalar(text("SELECT count(*) FROM document_chunks;"))
            emb_count = await conn.scalar(text("SELECT count(*) FROM chunk_embeddings;"))
            entity_count = await conn.scalar(text("SELECT count(*) FROM entities;"))
            doc_entity_count = await conn.scalar(text("SELECT count(*) FROM document_entities;"))
            rel_count = await conn.scalar(text("SELECT count(*) FROM relationships;"))
            job_count = await conn.scalar(text("SELECT count(*) FROM processing_jobs;"))
            search_count = await conn.scalar(text("SELECT count(*) FROM search_history;"))

            # Sources
            ia_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE source = 'internet_archive';"))
            loc_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE source = 'loc';"))

            # Processing Status
            pending_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE status = 'PENDING';"))
            proc_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE status IN ('PROCESSING', 'INGESTED');"))
            comp_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE status = 'READY';"))
            fail_count = await conn.scalar(text("SELECT count(*) FROM documents WHERE status = 'FAILED';"))

            # AI Providers in metadata
            gemini_enrichments = await conn.scalar(
                text("SELECT count(*) FROM document_metadata WHERE provenance::text ILIKE '%gemini%' OR ai_metadata->>'provider' ILIKE '%gemini%';")
            )
            mock_enrichments = await conn.scalar(
                text("SELECT count(*) FROM document_metadata WHERE provenance::text ILIKE '%mock%' OR ai_metadata->>'provider' ILIKE '%mock%';")
            )

            # Embeddings Breakdown
            real_embeddings = await conn.scalar(
                text("SELECT count(*) FROM chunk_embeddings WHERE model_name ILIKE '%gemini%' OR model_name ILIKE '%text-embedding%';")
            )
            mock_embeddings = await conn.scalar(
                text("SELECT count(*) FROM chunk_embeddings WHERE model_name ILIKE '%mock%';")
            )

        print("====================================================")
        print("                  DATABASE SUMMARY                  ")
        print("====================================================")
        print(f"Documents:             {doc_count}")
        print(f"Media Assets:          {media_count}")
        print(f"Metadata Records:      {meta_count}")
        print(f"Chunks:                {chunk_count}")
        print(f"Embeddings:            {emb_count}")
        print(f"Entities:              {entity_count}")
        print(f"Document-Entity Links: {doc_entity_count}")
        print(f"Relationships:         {rel_count}")
        print(f"Processing Jobs:       {job_count}")
        print(f"Search History:        {search_count}\n")

        print("SOURCES")
        print("-------")
        print(f"Internet Archive:      {ia_count}")
        print(f"Library of Congress:   {loc_count}\n")

        print("PROCESSING STATUS")
        print("-----------------")
        print(f"Pending:               {pending_count}")
        print(f"Processing:            {proc_count}")
        print(f"Completed:             {comp_count}")
        print(f"Failed:                {fail_count}\n")

        print("AI PROVIDERS")
        print("------------")
        print(f"Real Gemini enrichments: {gemini_enrichments}")
        print(f"Mock enrichments:        {mock_enrichments}\n")

        print("EMBEDDINGS")
        print("----------")
        print(f"Real embeddings:       {real_embeddings}")
        print(f"Mock embeddings:       {mock_embeddings}")
        print("====================================================\n")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(inspect_database())
