from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.entity import Entity
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.relationship import Relationship

router = APIRouter()


@router.get(
    "",
    summary="Archival Repository Statistics",
    description="Returns aggregate metrics across documents, physical assets, embeddings, and knowledge entities.",
)
async def get_archive_stats(session: AsyncSession = Depends(get_db)):
    doc_count = (await session.execute(select(func.count(Document.id)))).scalar() or 0
    media_count = (await session.execute(select(func.count(DocumentMediaAsset.id)))).scalar() or 0
    chunk_count = (await session.execute(select(func.count(DocumentChunk.id)))).scalar() or 0
    emb_count = (await session.execute(select(func.count(ChunkEmbedding.id)))).scalar() or 0
    entity_count = (await session.execute(select(func.count(Entity.id)))).scalar() or 0
    rel_count = (await session.execute(select(func.count(Relationship.id)))).scalar() or 0

    sources_q = await session.execute(
        select(Document.source, func.count(Document.id)).group_by(Document.source)
    )
    sources = {row[0]: row[1] for row in sources_q.fetchall()}

    formats_q = await session.execute(
        select(Document.record_type, func.count(Document.id)).group_by(Document.record_type)
    )
    formats = {row[0]: row[1] for row in formats_q.fetchall()}

    return {
        "documents": doc_count,
        "media_assets": media_count,
        "chunks": chunk_count,
        "embeddings": emb_count,
        "entities": entity_count,
        "relationships": rel_count,
        "sources": sources,
        "record_types": formats,
        "status": "online",
    }
