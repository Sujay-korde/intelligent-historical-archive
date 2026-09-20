import uuid
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.document import Document
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.entity import Entity
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.relationship import Relationship
from backend.app.models.job import ProcessingJob
from backend.app.models.search_history import SearchHistory


def test_model_instantiation_and_relationships():
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source="loc",
        source_id="loc_item_001",
        title="Historical Constitution Document 1787",
        description="Foundational constitutional draft",
        record_type="document",
        status="INGESTED",
        processing_stage="INITIAL",
    )
    assert doc.id == doc_id
    assert doc.source == "loc"
    assert doc.title == "Historical Constitution Document 1787"

    # Test Media Asset Model
    asset = DocumentMediaAsset(
        id=uuid.uuid4(),
        document_id=doc_id,
        asset_role="primary",
        media_type="document",
        mime_type="application/pdf",
        storage_key="documents/2026/09/loc_item_001.pdf",
    )
    assert asset.document_id == doc_id
    assert asset.asset_role == "primary"

    # Test Metadata Model
    meta = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc_id,
        creators=[{"name": "James Madison", "role": "Author"}],
        language="English",
        subjects=["History", "Law", "Constitution"],
    )
    assert meta.document_id == doc_id
    assert len(meta.creators) == 1
    assert meta.subjects == ["History", "Law", "Constitution"]

    # Test Document Chunk Model
    chunk_id = uuid.uuid4()
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        content="We the People of the United States, in Order to form a more perfect Union...",
        page_number=1,
        token_count=14,
    )
    assert chunk.document_id == doc_id
    assert chunk.chunk_index == 0

    # Test Chunk Embedding Model
    dummy_vector = [0.1] * 384
    embedding = ChunkEmbedding(
        id=uuid.uuid4(),
        chunk_id=chunk_id,
        model_name="all-MiniLM-L6-v2",
        model_version="1.0",
        dimension=384,
        embedding=dummy_vector,
    )
    assert embedding.chunk_id == chunk_id
    assert embedding.dimension == 384
    assert len(embedding.embedding) == 384

    # Test Entity & Relationship Models
    entity1_id = uuid.uuid4()
    entity2_id = uuid.uuid4()
    entity1 = Entity(
        id=entity1_id,
        name="James Madison",
        normalized_name="james madison",
        entity_type="PERSON",
        authority_uri="https://www.wikidata.org/wiki/Q11813",
    )
    entity2 = Entity(
        id=entity2_id,
        name="Philadelphia",
        normalized_name="philadelphia",
        entity_type="LOCATION",
    )
    assert entity1.normalized_name == "james madison"

    doc_entity = DocumentEntity(
        document_id=doc_id,
        entity_id=entity1_id,
        confidence=0.98,
        provenance="AI",
        relationship_type="AUTHOR",
    )
    assert doc_entity.relationship_type == "AUTHOR"

    rel = Relationship(
        id=uuid.uuid4(),
        source_entity_id=entity1_id,
        target_entity_id=entity2_id,
        relationship_type="LOCATED_IN",
        confidence=0.95,
        source_document_id=doc_id,
    )
    assert rel.relationship_type == "LOCATED_IN"

    # Test Processing Job Model
    job = ProcessingJob(
        id=uuid.uuid4(),
        document_id=doc_id,
        job_type="OCR_CHUNKING",
        status="PENDING",
        current_step="QUEUED",
        progress_pct=0,
    )
    assert job.status == "PENDING"
    assert job.current_step == "QUEUED"

    # Test Search History Model
    history = SearchHistory(
        id=uuid.uuid4(),
        query="Constitutional Convention 1787",
        filters={"subjects": ["Law"]},
        search_type="HYBRID",
        result_count=12,
    )
    assert history.query == "Constitutional Convention 1787"
    assert history.search_type == "HYBRID"
