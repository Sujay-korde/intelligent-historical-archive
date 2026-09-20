import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.repositories.chunk_repo import ChunkRepository
from backend.app.schemas.recommendation import RecommendationResponse
from backend.app.services.recommendation_service import RecommendationService


@pytest.mark.asyncio
async def test_recommendation_service_with_real_associations():
    # Document 1: Lincoln Biography
    doc1_id = uuid.uuid4()
    doc1 = Document(
        id=doc1_id,
        title="The Life and Public Services of Abraham Lincoln",
        description="Comprehensive biography of Lincoln",
        source="internet_archive",
        source_id="thelifeandpublic22681gut",
        record_type="document",
        status="READY",
    )
    doc1.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc1_id,
        creators=[{"name": "Charles Maltby", "role": "Author"}],
        subjects=["Civil War", "Presidency", "Lincoln"],
        ai_metadata={"historical_period": "American Civil War"},
    )
    doc1.media_assets = [
        DocumentMediaAsset(id=uuid.uuid4(), document_id=doc1_id, asset_role="primary", media_type="document", mime_type="text/plain", storage_key="doc1.txt")
    ]
    e_lincoln = Entity(id=uuid.uuid4(), name="Abraham Lincoln", entity_type="PERSON")
    doc1.entities = [DocumentEntity(document_id=doc1_id, entity_id=e_lincoln.id, entity=e_lincoln)]

    chunk1 = DocumentChunk(id=uuid.uuid4(), document_id=doc1_id, chunk_index=0, content="Lincoln speech and presidency")
    chunk1.embeddings = [
        ChunkEmbedding(id=uuid.uuid4(), chunk_id=chunk1.id, model_name="test-model", model_version="1.0", embedding=[0.5] * 384, is_active=True)
    ]
    doc1.chunks = [chunk1]

    # Document 2: Beecher Civil War Speech (High overlap in era, subject, and entity)
    doc2_id = uuid.uuid4()
    doc2 = Document(
        id=doc2_id,
        title="The War for the Union: A Lecture",
        description="Lecture on the Civil War and Union",
        source="internet_archive",
        source_id="warforunion00beec",
        record_type="document",
        status="READY",
    )
    doc2.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc2_id,
        creators=[{"name": "Henry Ward Beecher", "role": "Author"}],
        subjects=["Civil War", "Union", "Secession"],
        ai_metadata={"historical_period": "American Civil War"},
    )
    doc2.media_assets = [
        DocumentMediaAsset(id=uuid.uuid4(), document_id=doc2_id, asset_role="primary", media_type="document", mime_type="application/pdf", storage_key="doc2.pdf")
    ]
    doc2.entities = [DocumentEntity(document_id=doc2_id, entity_id=e_lincoln.id, entity=e_lincoln)]
    chunk2 = DocumentChunk(id=uuid.uuid4(), document_id=doc2_id, chunk_index=0, content="Beecher speech on the Union")
    chunk2.embeddings = [
        ChunkEmbedding(id=uuid.uuid4(), chunk_id=chunk2.id, model_name="test-model", model_version="1.0", embedding=[0.48] * 384, is_active=True)
    ]
    doc2.chunks = [chunk2]

    mock_session = AsyncMock()

    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id in" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [doc2]
            return mock_res
        if "where documents.id !=" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [doc2_id]
            return mock_res
        if "where documents.id =" in stmt_str:
            mock_res.scalar_one_or_none.return_value = doc1
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute

    # Mock chunk repository vector similarity search
    mock_chunk_repo = MagicMock(spec=ChunkRepository)
    mock_chunk_repo.vector_similarity_search = AsyncMock(
        return_value=[
            {"document_id": doc2_id, "similarity": 0.92, "distance": 0.08}
        ]
    )

    service = RecommendationService(session=mock_session, chunk_repo=mock_chunk_repo)

    resp = await service.get_recommendations(document_id=doc1_id, limit=3)
    assert isinstance(resp, RecommendationResponse)
    assert resp.source_document_id == doc1_id
    assert resp.total_recommendations == 1

    rec = resp.recommendations[0]
    assert rec.document.id == doc2_id
    assert rec.document.title == "The War for the Union: A Lecture"
    assert rec.score > 0.6
    assert rec.semantic_similarity == 0.92
    assert "Abraham Lincoln" in rec.shared_entities
    assert "Civil War" in rec.shared_subjects
    assert rec.shared_historical_period == "American Civil War"
    assert "Semantic similarity" in rec.explanation


@pytest.mark.asyncio
async def test_recommendation_api_endpoint():
    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()

    mock_service = AsyncMock(spec=RecommendationService)
    mock_service.get_recommendations.return_value = RecommendationResponse(
        source_document_id=doc1_id,
        total_recommendations=1,
        recommendations=[
            {
                "document": {
                    "id": doc2_id,
                    "title": "The War for the Union",
                    "description": "Historical Civil War lecture",
                    "source": "internet_archive",
                    "source_id": "warforunion00beec",
                    "record_type": "document",
                    "status": "READY",
                },
                "score": 0.88,
                "semantic_similarity": 0.91,
                "shared_entities": ["Abraham Lincoln"],
                "shared_subjects": ["Civil War"],
                "shared_historical_period": "American Civil War",
                "explanation": "Semantic similarity (0.91) + Shared entities: Abraham Lincoln",
                "preview": {"has_media": True, "media_type": "document", "mime_type": "application/pdf"},
            }
        ],
    )

    from backend.app.api.deps import get_recommendation_service
    app.dependency_overrides[get_recommendation_service] = lambda: mock_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/v1/recommendations/{doc1_id}?limit=2")
            assert res.status_code == 200
            data = res.json()
            assert data["source_document_id"] == str(doc1_id)
            assert data["total_recommendations"] == 1
            assert len(data["recommendations"]) == 1
            assert data["recommendations"][0]["document"]["title"] == "The War for the Union"
            assert data["recommendations"][0]["score"] == 0.88
    finally:
        app.dependency_overrides.clear()
