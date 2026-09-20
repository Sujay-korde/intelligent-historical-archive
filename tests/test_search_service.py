import math
import uuid
from typing import List
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from backend.app.main import app
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.repositories.search_repo import SearchRepository
from backend.app.schemas.search import (
    DocumentSummary,
    MatchedEntityItem,
    PreviewInformation,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from backend.app.search.query_normalizer import normalize_search_query
from backend.app.search.ranking.base import CandidateMatch
from backend.app.search.ranking.rrf_ranker import ReciprocalRankFusionRanker
from backend.app.services.search_service import SearchService


# ---------------------------------------------------------------------------
# 1. Query Normalization Tests
# ---------------------------------------------------------------------------

def test_query_normalizer_ligatures_and_typography():
    # Historical ligatures
    raw = "The cœval and præcedent treaties concerning the ambaſſador"
    clean = normalize_search_query(raw)
    assert "coeval" in clean
    assert "praecedent" in clean
    assert "ambassador" in clean

    # Smart typographic quotes and hyphens
    raw2 = "“Liberty and Union”—now and forever"
    clean2 = normalize_search_query(raw2)
    assert clean2 == '"Liberty and Union"-now and forever'

    # Excess whitespace
    raw3 = "   Abraham    Lincoln \n\t Address   "
    clean3 = normalize_search_query(raw3)
    assert clean3 == "Abraham Lincoln Address"


# ---------------------------------------------------------------------------
# 2. Modular Ranking Tests (RRF)
# ---------------------------------------------------------------------------

def test_rrf_ranker_logic():
    ranker = ReciprocalRankFusionRanker(k=60)

    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    doc_c = uuid.uuid4()

    # doc_a: rank 1 in semantic, rank 2 in keyword
    # doc_b: rank 1 in keyword, no semantic match
    # doc_c: rank 2 in semantic, no keyword match
    sem_cands = {
        doc_a: CandidateMatch(document_id=doc_a, rank=1, score=0.92, content="a", match_type="semantic"),
        doc_c: CandidateMatch(document_id=doc_c, rank=2, score=0.85, content="c", match_type="semantic"),
    }
    kw_cands = {
        doc_b: CandidateMatch(document_id=doc_b, rank=1, score=10.0, content="b", match_type="keyword"),
        doc_a: CandidateMatch(document_id=doc_a, rank=2, score=5.0, content="a", match_type="keyword"),
    }

    # With hybrid 0.7 sem / 0.3 kw: doc_a should rank #1 because it has both signals
    ranked = ranker.rank(
        semantic_candidates=sem_cands,
        keyword_candidates=kw_cands,
        semantic_weight=0.7,
        keyword_weight=0.3,
        limit=10,
    )

    assert len(ranked) == 3
    assert ranked[0][0] == doc_a  # doc_a ranks highest due to dual signals
    assert ranked[0][1] > ranked[1][1]
    # Check normalized score is bounded in [0.0, 1.0]
    for _, score in ranked:
        assert 0.0 <= score <= 1.0


def test_rrf_ranker_weight_biasing():
    ranker = ReciprocalRankFusionRanker(k=60)
    doc_sem = uuid.uuid4()
    doc_kw = uuid.uuid4()

    sem_cands = {doc_sem: CandidateMatch(document_id=doc_sem, rank=1, score=0.95, match_type="semantic")}
    kw_cands = {doc_kw: CandidateMatch(document_id=doc_kw, rank=1, score=15.0, match_type="keyword")}

    # Heavy semantic weighting
    ranked_sem_biased = ranker.rank(sem_cands, kw_cands, semantic_weight=0.9, keyword_weight=0.1)
    assert ranked_sem_biased[0][0] == doc_sem

    # Heavy keyword weighting
    ranked_kw_biased = ranker.rank(sem_cands, kw_cands, semantic_weight=0.1, keyword_weight=0.9)
    assert ranked_kw_biased[0][0] == doc_kw


# ---------------------------------------------------------------------------
# 3. Search Result Schema Compliance Tests
# ---------------------------------------------------------------------------

def test_search_result_item_structure():
    doc_id = uuid.uuid4()
    item = SearchResultItem(
        document=DocumentSummary(
            id=doc_id,
            title="Declaration of Independence",
            description="Founding document of 1776",
            source="loc",
            source_id="loc_1776_dec",
            record_type="document",
            source_url="https://loc.gov/item/1776",
            status="READY",
        ),
        relevance_score=0.9542,
        matching_snippet="...We hold these truths to be self-evident, that all men are created equal...",
        matched_metadata={"date": "1776-07-04", "creator": "Thomas Jefferson"},
        source="loc",
        entities=[
            MatchedEntityItem(name="Thomas Jefferson", entity_type="PERSON", confidence=0.99),
            MatchedEntityItem(name="Philadelphia", entity_type="LOCATION", confidence=0.95),
        ],
        available_preview_information=PreviewInformation(
            has_media=True,
            media_type="document",
            mime_type="application/pdf",
            storage_key="documents/1776.pdf",
            page_number=1,
            file_size_bytes=1024500,
        ),
        relevance_explanation="Semantic match (sim: 0.94, rank #1) + Keyword match (rank #1)",
    )

    # Verify all 7 required top-level attributes
    assert item.document.id == doc_id
    assert item.relevance_score == 0.9542
    assert "self-evident" in item.matching_snippet
    assert item.matched_metadata["creator"] == "Thomas Jefferson"
    assert item.source == "loc"
    assert len(item.entities) == 2
    assert item.available_preview_information.has_media is True
    assert item.available_preview_information.media_type == "document"

    # Verify backwards-compatible property accessors
    assert item.document_id == doc_id
    assert item.title == "Declaration of Independence"
    assert item.score == 0.9542
    assert item.snippet == item.matching_snippet


# ---------------------------------------------------------------------------
# 4. Search Service & Metadata Filtering Integration
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_archival_database():
    """Builds an in-memory collection of mock archival records representing diverse modalities."""
    records = []

    # Record 1: Civil War Speech (Henry Ward Beecher)
    doc1_id = uuid.uuid4()
    doc1 = Document(
        id=doc1_id,
        title="The War for the Union: A Lecture",
        description="A speech delivered by Henry Ward Beecher on the preservation of the Union and the abolition of slavery.",
        source="internet_archive",
        source_id="warforunion00beec",
        record_type="document",
        source_url="https://archive.org/details/warforunion00beec",
        status="READY",
    )
    doc1.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc1_id,
        creators=[{"name": "Henry Ward Beecher", "role": "Author"}],
        date_raw="1862",
        subjects=["Civil War", "Speeches", "Union", "Secession"],
        ai_metadata={"historical_period": "American Civil War", "summary": "Speech arguing for the preservation of the Union."},
    )
    doc1.media_assets = [
        DocumentMediaAsset(
            id=uuid.uuid4(),
            document_id=doc1_id,
            asset_role="primary",
            media_type="document",
            mime_type="application/pdf",
            storage_key="documents/warforunion00beec.pdf",
            page_number=1,
            file_size_bytes=1500000,
        )
    ]
    e_lincoln = Entity(id=uuid.uuid4(), name="Abraham Lincoln", entity_type="PERSON")
    e_beecher = Entity(id=uuid.uuid4(), name="Henry Ward Beecher", entity_type="PERSON")
    doc1.entities = [
        DocumentEntity(document_id=doc1_id, entity_id=e_beecher.id, confidence=0.98, entity=e_beecher),
        DocumentEntity(document_id=doc1_id, entity_id=e_lincoln.id, confidence=0.90, entity=e_lincoln),
    ]

    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc1_id,
        chunk_index=0,
        page_number=1,
        content="The war for the Union is a conflict for the principles of constitutional liberty. No state can withdraw from the compact.",
    )

    # Record 2: Lincoln Biography (Texts)
    doc2_id = uuid.uuid4()
    doc2 = Document(
        id=doc2_id,
        title="The Life and Public Services of Abraham Lincoln",
        description="A comprehensive biographical account of President Abraham Lincoln, his career in Illinois, and presidential leadership.",
        source="internet_archive",
        source_id="thelifeandpublic22681gut",
        record_type="document",
        source_url="https://archive.org/details/thelifeandpublic22681gut",
        status="READY",
    )
    doc2.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc2_id,
        creators=[{"name": "Charles Maltby", "role": "Author"}],
        date_raw="1884",
        subjects=["Abraham Lincoln", "Biography", "Presidency", "Illinois"],
        ai_metadata={"historical_period": "19th Century American History"},
    )
    doc2.media_assets = [
        DocumentMediaAsset(
            id=uuid.uuid4(),
            document_id=doc2_id,
            asset_role="primary",
            media_type="document",
            mime_type="text/plain",
            storage_key="documents/thelifeandpublic22681gut.txt",
            page_number=1,
            file_size_bytes=450000,
        )
    ]
    doc2.entities = [
        DocumentEntity(document_id=doc2_id, entity_id=e_lincoln.id, confidence=0.99, entity=e_lincoln),
    ]
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc2_id,
        chunk_index=0,
        page_number=1,
        content="Abraham Lincoln was elected sixteenth President of the United States. His early years in Illinois formed his conviction against slavery.",
    )

    # Record 3: Abolitionist Manuscript Letter (Garrison)
    doc3_id = uuid.uuid4()
    doc3 = Document(
        id=doc3_id,
        title="Letter to Dear Garrison",
        description="Handwritten correspondence regarding the anti-slavery movement and abolitionist meetings.",
        source="internet_archive",
        source_id="lettertodeargarr00john_86",
        record_type="manuscript",
        source_url="https://archive.org/details/lettertodeargarr00john_86",
        status="READY",
    )
    doc3.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc3_id,
        creators=[{"name": "Oliver Johnson", "role": "Author"}],
        date_raw="1854",
        subjects=["Abolition", "William Lloyd Garrison", "Correspondence", "Manuscript"],
        ai_metadata={"historical_period": "Antebellum America"},
    )
    doc3.media_assets = [
        DocumentMediaAsset(
            id=uuid.uuid4(),
            document_id=doc3_id,
            asset_role="primary",
            media_type="manuscript",
            mime_type="application/pdf",
            storage_key="manuscripts/lettertodeargarr00john_86.pdf",
            page_number=1,
            file_size_bytes=220000,
        )
    ]
    e_garrison = Entity(id=uuid.uuid4(), name="William Lloyd Garrison", entity_type="PERSON")
    doc3.entities = [
        DocumentEntity(document_id=doc3_id, entity_id=e_garrison.id, confidence=0.96, entity=e_garrison)
    ]
    chunk3 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc3_id,
        chunk_index=0,
        page_number=1,
        content="Dear Garrison, our abolitionist convention convened yesterday to renew our protest against the Fugitive Slave Law.",
    )

    # Record 4: Audio Speech (1945 Denmark Liberation)
    doc4_id = uuid.uuid4()
    doc4 = Document(
        id=doc4_id,
        title="4 May 1945 Liberation of Denmark Speech",
        description="Historic BBC radio broadcast announcing the liberation of Denmark from German occupation at the conclusion of World War II.",
        source="internet_archive",
        source_id="1945speech",
        record_type="audio",
        source_url="https://archive.org/details/1945speech",
        status="READY",
    )
    doc4.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc4_id,
        creators=[{"name": "Johs. G. Sorensen", "role": "Speaker"}],
        date_raw="1945-05-04",
        subjects=["Speech", "Liberation", "Denmark", "World War II"],
        ai_metadata={"historical_period": "World War II"},
    )
    doc4.media_assets = [
        DocumentMediaAsset(
            id=uuid.uuid4(),
            document_id=doc4_id,
            asset_role="primary",
            media_type="audio",
            mime_type="audio/mp4",
            storage_key="audio/1945speech.m4a",
            file_size_bytes=7478024,
        )
    ]
    e_denmark = Entity(id=uuid.uuid4(), name="Denmark", entity_type="LOCATION")
    doc4.entities = [
        DocumentEntity(document_id=doc4_id, entity_id=e_denmark.id, confidence=0.95, entity=e_denmark)
    ]
    chunk4 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc4_id,
        chunk_index=0,
        page_number=1,
        content="In this moment, the German forces in Denmark have surrendered. Denmark is free once again.",
    )

    # Record 5: Mahatma Gandhi Speech (Audio / Independence)
    doc5_id = uuid.uuid4()
    doc5 = Document(
        id=doc5_id,
        title="Mahatma Gandhi speech at the closing session of the Inter-Asian Relations Conference",
        description="Closing address delivered by Mahatma Gandhi in New Delhi on peace, non-violence, and Asian solidarity.",
        source="internet_archive",
        source_id="aumgen1947040201",
        record_type="audio",
        source_url="https://archive.org/details/aumgen1947040201",
        status="READY",
    )
    doc5.doc_metadata = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc5_id,
        creators=[{"name": "Mahatma Gandhi", "role": "Speaker"}],
        date_raw="1947-04-02",
        subjects=["Gandhi", "Peace", "New Delhi", "Speech"],
        ai_metadata={"historical_period": "Post-Colonial Era"},
    )
    doc5.media_assets = [
        DocumentMediaAsset(
            id=uuid.uuid4(),
            document_id=doc5_id,
            asset_role="primary",
            media_type="audio",
            mime_type="audio/mpeg",
            storage_key="audio/aumgen1947040201.mp3",
            file_size_bytes=18364741,
        )
    ]
    e_gandhi = Entity(id=uuid.uuid4(), name="Mahatma Gandhi", entity_type="PERSON")
    doc5.entities = [
        DocumentEntity(document_id=doc5_id, entity_id=e_gandhi.id, confidence=0.99, entity=e_gandhi)
    ]
    chunk5 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc5_id,
        chunk_index=0,
        page_number=1,
        content="If you want to give a message again to the West, it must be the message of 'Love' and 'Truth'.",
    )

    all_docs = [doc1, doc2, doc3, doc4, doc5]
    all_chunks = [
        (chunk1, doc1),
        (chunk2, doc2),
        (chunk3, doc3),
        (chunk4, doc4),
        (chunk5, doc5),
    ]

    return all_docs, all_chunks


@pytest.mark.asyncio
async def test_search_repository_vector_and_keyword_flow(mock_archival_database):
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    # Embed chunks
    chunk_embeddings = []
    for chunk, doc in all_chunks:
        vec = await provider.embed_text(chunk.content)
        emb = ChunkEmbedding(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            model_name="mock-feature-hash-v1",
            model_version="1.0.0",
            embedding=vec,
            is_active=True,
        )
        chunk_embeddings.append((chunk, emb, doc))

    # Mock async session
    mock_session = AsyncMock()

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        mock_res = MagicMock()

        # Check if querying Document with ID filter (for hydration)
        if "from documents" in stmt_str and "where documents.id =" in stmt_str:
            # Extract doc_id from statement or return corresponding doc
            for doc in all_docs:
                if str(doc.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = doc
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[0]
            return mock_res

        # If vector query
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = chunk_embeddings
            return mock_res

        # If document keyword query
        if "from documents" in stmt_str and "chunk_embeddings" not in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_docs
            return mock_res

        # If chunk keyword query
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, _ in all_chunks
            ]
            return mock_res

        mock_res.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        return mock_res

    mock_session.execute.side_effect = mock_execute
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    service = SearchService(session=mock_session, embedding_provider=provider)

    # Execute search
    req = SearchRequest(query="war for the union civil war", search_type="hybrid")
    res = await service.search(req)

    assert isinstance(res, SearchResponse)
    assert res.query == "war for the union civil war"
    assert res.total_results > 0
    assert len(res.results) > 0

    first = res.results[0]
    assert first.document.title is not None
    assert first.relevance_score > 0.0
    assert len(first.matching_snippet) > 0
    assert first.source == "internet_archive"
    assert first.available_preview_information is not None


# ---------------------------------------------------------------------------
# 5. Demonstration Queries with Real Prototype Dataset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_demonstration_query_1_civil_war_speech(mock_archival_database):
    """
    Demo Query 1: 'civil war union secession speech'
    Expected top match: 'The War for the Union: A Lecture' by Henry Ward Beecher
    """
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            for d in all_docs:
                if str(d.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = d
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[0]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = chunk_embeddings
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_docs
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, _ in all_chunks
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    service = SearchService(session=mock_session, embedding_provider=provider)

    req = SearchRequest(query="civil war union secession speech", search_type="hybrid")
    resp = await service.search(req)

    assert resp.total_results > 0
    top = resp.results[0]
    assert "War for the Union" in top.document.title
    assert top.source == "internet_archive"
    assert top.available_preview_information.has_media is True
    assert top.available_preview_information.media_type == "document"
    assert any(e.name == "Henry Ward Beecher" for e in top.entities)


@pytest.mark.asyncio
async def test_demonstration_query_2_lincoln_biography_with_filters(mock_archival_database):
    """
    Demo Query 2: 'Abraham Lincoln president Illinois emancipation'
    Filters: source='internet_archive', record_type='document'
    Expected match: 'The Life and Public Services of Abraham Lincoln'
    """
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            for d in all_docs:
                if str(d.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = d
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[1]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = chunk_embeddings
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_docs
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, _ in all_chunks
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    service = SearchService(session=mock_session, embedding_provider=provider)

    req = SearchRequest(
        query="Abraham Lincoln president Illinois emancipation",
        source="internet_archive",
        record_type="document",
        search_type="hybrid",
    )
    resp = await service.search(req)

    assert resp.total_results > 0
    # Must find Lincoln's biography
    titles = [r.document.title for r in resp.results]
    assert any("Abraham Lincoln" in t for t in titles)
    lincoln_res = next(r for r in resp.results if "Abraham Lincoln" in r.document.title)
    assert lincoln_res.document.record_type == "document"
    assert lincoln_res.source == "internet_archive"
    assert "lincoln" in lincoln_res.matching_snippet.lower()


@pytest.mark.asyncio
async def test_demonstration_query_3_abolitionist_manuscript(mock_archival_database):
    """
    Demo Query 3: 'William Lloyd Garrison letter abolitionist manuscript'
    Filters: record_type='manuscript'
    Expected match: 'Letter to Dear Garrison'
    """
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            for d in all_docs:
                if str(d.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = d
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[2]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            # Filter manuscripts if SQL requested it
            if "record_type" in stmt_str:
                mock_res.all.return_value = [ce for ce in chunk_embeddings if ce[2].record_type == "manuscript"]
            else:
                mock_res.all.return_value = chunk_embeddings
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [d for d in all_docs if d.record_type == "manuscript"]
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, d in all_chunks if d.record_type == "manuscript"
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    service = SearchService(session=mock_session, embedding_provider=provider)

    req = SearchRequest(
        query="William Lloyd Garrison letter abolitionist manuscript",
        record_type="manuscript",
    )
    resp = await service.search(req)

    assert resp.total_results > 0
    top = resp.results[0]
    assert "Letter to Dear Garrison" in top.document.title
    assert top.document.record_type == "manuscript"
    assert top.available_preview_information.media_type == "manuscript"


@pytest.mark.asyncio
async def test_demonstration_query_4_denmark_liberation_audio_date_filter(mock_archival_database):
    """
    Demo Query 4: 'Denmark liberation speech 1945 May'
    Filters: record_type='audio', date_start='1945'
    Expected match: '4 May 1945 Liberation of Denmark Speech'
    """
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            for d in all_docs:
                if str(d.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = d
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[3]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = [ce for ce in chunk_embeddings if ce[2].record_type == "audio"]
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [d for d in all_docs if d.record_type == "audio"]
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, d in all_chunks if d.record_type == "audio"
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    service = SearchService(session=mock_session, embedding_provider=provider)

    req = SearchRequest(
        query="Denmark liberation speech 1945 May",
        record_type="audio",
        date_start="1945",
    )
    resp = await service.search(req)

    assert resp.total_results > 0
    top = resp.results[0]
    assert "Liberation of Denmark" in top.document.title
    assert top.document.record_type == "audio"
    assert top.available_preview_information.media_type == "audio"
    assert "1945" in top.matched_metadata.get("date", "")


@pytest.mark.asyncio
async def test_demonstration_query_5_gandhi_prayer_speech_creator_filter(mock_archival_database):
    """
    Demo Query 5: 'Mahatma Gandhi prayer speech New Delhi Inter-Asian Relations'
    Filters: creator='Mahatma Gandhi'
    Expected match: Mahatma Gandhi address
    """
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            for d in all_docs:
                if str(d.id) in stmt_str:
                    mock_res.scalar_one_or_none.return_value = d
                    return mock_res
            mock_res.scalar_one_or_none.return_value = all_docs[4]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = chunk_embeddings
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_docs
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, _ in all_chunks
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    service = SearchService(session=mock_session, embedding_provider=provider)

    req = SearchRequest(
        query="Mahatma Gandhi prayer speech New Delhi Inter-Asian Relations",
        creator="Mahatma Gandhi",
    )
    resp = await service.search(req)

    assert resp.total_results > 0
    top = resp.results[0]
    assert "Mahatma Gandhi" in top.document.title
    assert top.matched_metadata["creator"] == "Mahatma Gandhi"


# ---------------------------------------------------------------------------
# 6. FastAPI Versioned Endpoint HTTP Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_api_post_endpoint(mock_archival_database):
    all_docs, all_chunks = mock_archival_database
    provider = MockEmbeddingProvider(dimension=384)

    chunk_embeddings = [
        (c, ChunkEmbedding(id=uuid.uuid4(), chunk_id=c.id, model_name=provider.model_name, model_version="1.0.0", embedding=await provider.embed_text(c.content), is_active=True), d)
        for c, d in all_chunks
    ]

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "where documents.id =" in stmt_str:
            mock_res.scalar_one_or_none.return_value = all_docs[0]
            return mock_res
        if "chunk_embeddings" in stmt_str:
            mock_res.all.return_value = chunk_embeddings
            return mock_res
        if "from documents" in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_docs
            return mock_res
        if "from document_chunks" in stmt_str:
            mock_res.all.return_value = [
                MagicMock(document_id=c.document_id, chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
                for c, _ in all_chunks
            ]
            return mock_res
        return mock_res

    mock_session.execute.side_effect = mock_execute
    mock_service = SearchService(session=mock_session, embedding_provider=provider)

    # Dependency override
    from backend.app.api.deps import get_search_service
    app.dependency_overrides[get_search_service] = lambda: mock_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Test POST /api/v1/search
            post_payload = {
                "query": "civil war union",
                "search_type": "hybrid",
                "limit": 5,
            }
            res = await client.post("/api/v1/search", json=post_payload)
            assert res.status_code == 200
            data = res.json()
            assert data["query"] == "civil war union"
            assert data["total_results"] > 0
            assert len(data["results"]) > 0
            first = data["results"][0]
            assert "document" in first
            assert "relevance_score" in first
            assert "matching_snippet" in first
            assert "matched_metadata" in first
            assert "source" in first
            assert "entities" in first
            assert "available_preview_information" in first

            # 2. Test GET /api/v1/search
            get_res = await client.get("/api/v1/search?q=civil+war+union&limit=3")
            assert get_res.status_code == 200
            get_data = get_res.json()
            assert get_data["query"] == "civil war union"
            assert len(get_data["results"]) > 0

            # 3. Test 422 on empty query
            empty_res = await client.post("/api/v1/search", json={"query": ""})
            assert empty_res.status_code == 422

    finally:
        app.dependency_overrides.clear()
