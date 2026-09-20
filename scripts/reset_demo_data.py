import asyncio
import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings


async def reset_demo_data():
    print("====================================================")
    print("              RESETTING DEMO / TEST DATA            ")
    print("====================================================\n")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    tables_to_clear = [
        "relationships",
        "document_entities",
        "entities",
        "chunk_embeddings",
        "document_chunks",
        "document_metadata",
        "document_media_assets",
        "processing_jobs",
        "search_history",
        "documents",
    ]

    try:
        async with engine.begin() as conn:
            for t in tables_to_clear:
                await conn.execute(text(f"TRUNCATE TABLE {t} CASCADE;"))
                print(f"Cleared table: {t}")

        print("\nDemo data successfully reset.")
        print("Schema, Alembic migrations, and physical raw storage remain intact.")
        print("====================================================\n")
    except Exception as e:
        print(f"Error resetting demo data: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_demo_data())
