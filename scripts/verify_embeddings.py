import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider


SAMPLE_TEXT_1 = "The Battle of Gettysburg was fought from July 1 to July 3, 1863, in and around the town of Gettysburg, Pennsylvania."
SAMPLE_TEXT_2 = "Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty."


async def verify_embeddings() -> bool:
    print("====================================================")
    print("            REAL EMBEDDINGS & PGVECTOR VERIFICATION ")
    print("====================================================\n")

    results: Dict[str, bool] = {}

    provider = GeminiEmbeddingProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
    )

    # 1. Provider & Model
    results["provider"] = provider is not None
    results["real_model"] = "gemini" in provider.model_name.lower() or "text-embedding" in provider.model_name.lower()

    # 2. Vector Generated
    try:
        vectors = await provider.embed_texts([SAMPLE_TEXT_1, SAMPLE_TEXT_2])
        results["vector_generated"] = len(vectors) == 2 and len(vectors[0]) > 0
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return False

    v1, v2 = vectors[0], vectors[1]

    # 3. Vector Dimension
    results["vector_dimension"] = (len(v1) == settings.EMBEDDING_DIMENSION)

    # 4. No Mock Hashing check
    # MockEmbeddingProvider produces sparse/repeated patterns with feature hashing
    # Real dense embeddings have continuous float distributions with high variance
    is_dense_floats = (
        isinstance(v1[0], float)
        and len(set(round(x, 4) for x in v1[:50])) > 25
    )
    results["no_mock_hashing"] = is_dense_floats

    # 5. Live pgvector Insert & Retrieval
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    test_doc_id = uuid.uuid4()
    test_chunk_id = uuid.uuid4()
    test_emb_id = uuid.uuid4()

    try:
        async with session_maker() as session:
            # Create parent document & chunk
            doc = Document(
                id=test_doc_id,
                source="verification",
                source_id=f"emb-test-{test_doc_id}",
                title="Embedding Verification Test Doc",
                record_type="document",
                status="TEST",
            )
            session.add(doc)

            chunk = DocumentChunk(
                id=test_chunk_id,
                document_id=test_doc_id,
                chunk_index=0,
                content=SAMPLE_TEXT_1,
                page_number=1,
            )
            session.add(chunk)

            # Insert pgvector chunk embedding
            chunk_emb = ChunkEmbedding(
                id=test_emb_id,
                chunk_id=test_chunk_id,
                model_name=provider.model_name,
                model_version=provider.model_version,
                dimension=len(v1),
                embedding=v1,
                is_active=True,
            )
            session.add(chunk_emb)
            await session.commit()

        results["pgvector_insert"] = True

        # 6. Vector Retrieval
        async with session_maker() as session:
            fetched_emb = await session.get(ChunkEmbedding, test_emb_id)
            results["vector_retrieval"] = (
                fetched_emb is not None
                and len(fetched_emb.embedding) == len(v1)
            )

        # 7. Actual pgvector Cosine Distance Query (<=> operator)
        async with session_maker() as session:
            # Execute native pgvector cosine similarity search
            vec_literal = "[" + ",".join(str(x) for x in v2) + "]"
            sql = text(
                """
                SELECT chunk_id, embedding <=> :query_vector AS distance
                FROM chunk_embeddings
                WHERE id = :target_id
                """
            )
            res = await session.execute(sql, {"query_vector": vec_literal, "target_id": test_emb_id})
            row = res.fetchone()
            if row:
                distance = float(row[1])
                # Cosine distance should be a reasonable float between 0.0 and 2.0
                results["similarity_query"] = (0.0 <= distance <= 2.0)
            else:
                results["similarity_query"] = False

        # Clean up test records
        async with session_maker() as session:
            to_delete = await session.get(Document, test_doc_id)
            if to_delete:
                await session.delete(to_delete)
                await session.commit()

    except Exception as e:
        print(f"PostgreSQL/pgvector test failed: {e}")
        results["pgvector_insert"] = False
        results["vector_retrieval"] = False
        results["similarity_query"] = False
    finally:
        await engine.dispose()

    # Output formatted checklist
    print(f"Embedding Provider ........... {'PASS' if results.get('provider') else 'FAIL'}")
    print(f"Real Model ................... {'PASS' if results.get('real_model') else 'FAIL'}")
    print(f"Vector Generated ............. {'PASS' if results.get('vector_generated') else 'FAIL'}")
    print(f"Vector Dimension ............. {'PASS' if results.get('vector_dimension') else 'FAIL'} ({provider.dimension}d)")
    print(f"No Mock Hashing .............. {'PASS' if results.get('no_mock_hashing') else 'FAIL'}")
    print(f"pgvector Insert .............. {'PASS' if results.get('pgvector_insert') else 'FAIL'}")
    print(f"Vector Retrieval ............. {'PASS' if results.get('vector_retrieval') else 'FAIL'}")
    print(f"Similarity Query ............. {'PASS' if results.get('similarity_query') else 'FAIL'}")

    all_passed = all(results.values())
    print("\n----------------------------------------------------")
    if all_passed:
        print("RESULT: REAL EMBEDDINGS VERIFIED")
    else:
        print("RESULT: REAL EMBEDDINGS VERIFICATION FAILED")
    print("----------------------------------------------------\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(verify_embeddings())
    sys.exit(0 if success else 1)
