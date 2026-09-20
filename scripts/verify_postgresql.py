import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.app.core.config import settings
from backend.app.models import (
    Base,
    Document,
    DocumentMediaAsset,
    DocumentMetadata,
    DocumentChunk,
    ChunkEmbedding,
    Entity,
    DocumentEntity,
    Relationship,
    ProcessingJob,
    SearchHistory,
)


EXPECTED_TABLES = [
    "documents",
    "document_media_assets",
    "document_metadata",
    "document_chunks",
    "chunk_embeddings",
    "entities",
    "document_entities",
    "relationships",
    "processing_jobs",
    "search_history",
]


async def verify_postgresql() -> bool:
    print("====================================================")
    print("          POSTGRESQL & PGVECTOR VERIFICATION        ")
    print("====================================================\n")

    results: Dict[str, bool] = {}

    # 1. Connection check (asyncpg)
    try:
        async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with async_engine.connect() as conn:
            val = await conn.scalar(text("SELECT 1;"))
            results["connection"] = (val == 1)
    except Exception as e:
        print(f"Connection failed: {e}")
        results["connection"] = False
        print("PostgreSQL Connection ........ FAIL")
        print(f"\nRoot Cause: Could not connect to {settings.DATABASE_URL}: {e}")
        return False

    print("PostgreSQL Connection ........ PASS")

    # 2. Database existence check
    try:
        async with async_engine.connect() as conn:
            current_db = await conn.scalar(text("SELECT current_database();"))
            archive_db_exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'archive_db';")
            )
            results["database_exists"] = bool(current_db and archive_db_exists)
    except Exception as e:
        results["database_exists"] = False
    print(f"Database Exists .............. {'PASS' if results.get('database_exists') else 'FAIL'}")

    # 3. pgvector extension check
    try:
        async with async_engine.connect() as conn:
            ext = await conn.scalar(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            )
            results["pgvector"] = (ext == "vector")
    except Exception as e:
        results["pgvector"] = False
    print(f"pgvector Extension ........... {'PASS' if results.get('pgvector') else 'FAIL'}")

    # 4. Alembic Migration check
    try:
        async with async_engine.connect() as conn:
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version;"))
            results["alembic"] = bool(revision)
    except Exception as e:
        results["alembic"] = False
    print(f"Alembic Migration ............ {'PASS' if results.get('alembic') else 'FAIL'}")

    # 5. 10 Expected tables check
    sync_engine = create_engine(settings.DATABASE_SYNC_URL)
    inspector = inspect(sync_engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [t for t in EXPECTED_TABLES if t not in existing_tables]
    results["tables"] = (len(missing_tables) == 0)
    print(f"10 Tables .................... {'PASS' if results['tables'] else 'FAIL'}")
    if missing_tables:
        print(f"   Missing tables: {missing_tables}")

    # 6. Foreign Keys check
    try:
        fk_doc_media = inspector.get_foreign_keys("document_media_assets")
        fk_doc_meta = inspector.get_foreign_keys("document_metadata")
        fk_chunks = inspector.get_foreign_keys("document_chunks")
        results["foreign_keys"] = bool(fk_doc_media and fk_doc_meta and fk_chunks)
    except Exception:
        results["foreign_keys"] = False
    print(f"Foreign Keys ................. {'PASS' if results['foreign_keys'] else 'FAIL'}")

    # 7. Indexes check
    try:
        indexes = inspector.get_indexes("documents")
        results["indexes"] = len(indexes) > 0
    except Exception:
        results["indexes"] = False
    print(f"Indexes ...................... {'PASS' if results['indexes'] else 'FAIL'}")

    # 8. CRUD Roundtrip check
    async_session = async_sessionmaker(async_engine, expire_on_commit=False)
    test_doc_id = uuid.uuid4()
    crud_success = False
    try:
        async with async_session() as session:
            # Create
            test_doc = Document(
                id=test_doc_id,
                source="verification_test",
                source_id=f"test-{test_doc_id}",
                title="PostgreSQL Integration Test Document",
                record_type="document",
                status="TEST",
            )
            session.add(test_doc)
            await session.commit()

        async with async_session() as session:
            # Read
            fetched = await session.get(Document, test_doc_id)
            assert fetched is not None and fetched.title == "PostgreSQL Integration Test Document"

            # Update
            fetched.title = "PostgreSQL Integration Test Document Updated"
            await session.commit()

        async with async_session() as session:
            # Verify Update and Delete
            updated = await session.get(Document, test_doc_id)
            assert updated.title == "PostgreSQL Integration Test Document Updated"
            await session.delete(updated)
            await session.commit()

        async with async_session() as session:
            deleted = await session.get(Document, test_doc_id)
            assert deleted is None

        crud_success = True
    except Exception as e:
        print(f"CRUD Error: {e}")
        crud_success = False

    results["crud"] = crud_success
    print(f"CRUD Roundtrip ............... {'PASS' if results['crud'] else 'FAIL'}")

    # 9. Vector Column check
    try:
        cols = {c["name"]: c for c in inspector.get_columns("chunk_embeddings")}
        embedding_col = cols.get("embedding")
        results["vector_column"] = embedding_col is not None and "VECTOR" in str(embedding_col["type"]).upper()
    except Exception as e:
        results["vector_column"] = False
    print(f"Vector Column ................ {'PASS' if results['vector_column'] else 'FAIL'}")

    # Final verdict
    all_passed = all(results.values())
    print("\n----------------------------------------------------")
    if all_passed:
        print("RESULT: POSTGRESQL VERIFIED")
    else:
        print("RESULT: POSTGRESQL VERIFICATION FAILED")
        failed = [k for k, v in results.items() if not v]
        print(f"Failed checks: {failed}")
    print("----------------------------------------------------\n")

    await async_engine.dispose()
    sync_engine.dispose()
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(verify_postgresql())
    sys.exit(0 if success else 1)
