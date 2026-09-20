import math
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from ai.embeddings.factory import create_embedding_provider
from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from ai.interfaces.embedding import EmbeddingProvider
from backend.app.core.config import settings
from backend.app.models.chunk import DocumentChunk
from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.models.document import Document
from backend.app.repositories.chunk_repo import ChunkRepository
from processing.base import ExtractedContent, ExtractedPage
from processing.chunking.base import BaseChunker, ChunkDTO, EmbeddedChunkDTO
from processing.chunking.factory import get_chunker, list_chunkers, register_chunker
from processing.chunking.page_chunker import PageChunker
from processing.chunking.text_chunker import TextChunker
from processing.processors.pdf_processor import PDFProcessor
from processing.processors.text_processor import TextProcessor
from processing.services.embedding_pipeline_service import EmbeddingPipelineService


DATA_DIR = Path("storage/data")
PDF_PATH = DATA_DIR / "documents" / "internet_archive" / "warforunion00beec.pdf"
TEXT_PATH = DATA_DIR / "documents" / "internet_archive" / "thelifeandpublic22681gut.txt"


# ---------------------------------------------------------------------------
# 1. Chunking Abstraction & Strategies Tests
# ---------------------------------------------------------------------------

def test_text_chunker_strategy():
    chunker = TextChunker()
    assert chunker.strategy_name == "TextChunker"

    sample_text = (
        "The American Civil War was fought between 1861 and 1865. "
        "The Union faced the Confederacy across dozens of battlefields.\n\n"
        "President Abraham Lincoln issued the Emancipation Proclamation in 1863, "
        "redefining the war as a struggle for human freedom and liberty.\n\n"
        "At Gettysburg, Lincoln delivered his brief but immortal address "
        "dedicating the soldiers' cemetery."
    )
    content = ExtractedContent(
        pages=[ExtractedPage(page_number=1, text=sample_text)],
        total_pages=1,
        full_text=sample_text,
    )

    chunks = chunker.chunk(content, max_tokens=30, overlap=5)
    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.content.strip() != ""
        assert c.page_number == 1
        assert c.token_count > 0


def test_text_chunker_overlap():
    chunker = TextChunker()
    # Create paragraphs long enough to trigger multiple chunks
    p1 = "First paragraph: " + ("Historical records from the Library of Congress. " * 15)
    p2 = "Second paragraph: " + ("National Archives and Records Administration preservation. " * 15)
    content = ExtractedContent(
        pages=[ExtractedPage(page_number=1, text=f"{p1}\n\n{p2}")],
        total_pages=1,
        full_text=f"{p1}\n\n{p2}",
    )

    chunks = chunker.chunk(content, max_tokens=50, overlap=10)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_page_chunker_strategy():
    chunker = PageChunker()
    assert chunker.strategy_name == "PageChunker"

    pages = [
        ExtractedPage(page_number=1, text="Page 1: Archival record of executive orders."),
        ExtractedPage(page_number=2, text="Page 2: Congressional debate on constitutional amendments."),
        ExtractedPage(page_number=3, text="Page 3: Ratification signatures and official seals."),
    ]
    content = ExtractedContent(
        pages=pages,
        total_pages=3,
        full_text="\n\n".join(p.text for p in pages),
    )

    chunks = chunker.chunk(content, max_tokens=100)
    assert len(chunks) == 3
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.page_number == i + 1
        assert f"Page {i + 1}" in c.content


def test_chunker_factory_and_registration():
    # Strategy discovery
    chunkers = list_chunkers()
    assert "paragraph" in chunkers
    assert "page" in chunkers

    c_text = get_chunker("paragraph")
    assert isinstance(c_text, TextChunker)

    c_page = get_chunker("page")
    assert isinstance(c_page, PageChunker)

    # Custom chunker registration
    class CustomHistoricalChunker(BaseChunker):
        strategy_name = "CustomHistorical"

        def chunk(self, content, max_tokens=500, overlap=50):
            return [
                ChunkDTO(
                    chunk_index=0,
                    content="custom chunk content",
                    page_number=1,
                    token_count=3,
                )
            ]

    register_chunker("custom", CustomHistoricalChunker)
    c_custom = get_chunker("custom")
    assert isinstance(c_custom, CustomHistoricalChunker)
    assert c_custom.strategy_name == "CustomHistorical"


# ---------------------------------------------------------------------------
# 2. Decoupled Embedding Provider Interface & Multi-Model Support
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_embedding_provider_interface():
    provider = MockEmbeddingProvider(dimension=384, model_version="1.0.0")
    assert isinstance(provider, EmbeddingProvider)
    assert provider.dimension == 384
    assert provider.model_name == "mock-feature-hash-v1"
    assert provider.model_version == "1.0.0"

    # Single text embedding
    vec = await provider.embed_text("Declaration of Independence July 4 1776")
    assert isinstance(vec, list)
    assert len(vec) == 384
    # Check L2 unit normalization: sum(v^2) == 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4

    # Batch embedding
    texts = [
        "President Abraham Lincoln",
        "General Ulysses S. Grant",
        "Battle of Gettysburg Pennsylvania",
    ]
    vecs = await provider.embed_texts(texts)
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 384
        assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_mock_embedding_provider_determinism():
    provider = MockEmbeddingProvider(dimension=384)
    v1 = await provider.embed_text("Thomas Jefferson drafted the Declaration")
    v2 = await provider.embed_text("Thomas Jefferson drafted the Declaration")
    v3 = await provider.embed_text("Alexander Hamilton published the Federalist Papers")

    # Exact match for identical input
    assert v1 == v2
    # Distinct vector for different input
    assert v1 != v3


@pytest.mark.asyncio
async def test_multi_model_support_different_dimensions():
    # Demonstrates system supporting different models/dimensions (e.g. 384 vs 768)
    p384 = MockEmbeddingProvider(dimension=384)
    p768 = MockEmbeddingProvider(dimension=768)

    v384 = await p384.embed_text("Constitution of the United States")
    v768 = await p768.embed_text("Constitution of the United States")

    assert len(v384) == 384
    assert len(v768) == 768


def test_embedding_factory():
    provider = create_embedding_provider(provider_type="mock")
    assert isinstance(provider, EmbeddingProvider)
    assert provider.dimension == settings.EMBEDDING_DIMENSION


# ---------------------------------------------------------------------------
# 3. Chunk Retention Field Verification
# ---------------------------------------------------------------------------

def test_embedded_chunk_dto_retention_fields():
    doc_id = uuid.uuid4()
    c_id = uuid.uuid4()
    dummy_vec = [0.05] * 384

    # Verify all 8 required fields:
    # 1. document_id
    # 2. chunk_id
    # 3. chunk_index
    # 4. content
    # 5. page_number
    # 6. embedding
    # 7. embedding_model
    # 8. embedding_model_version
    chunk_dto = EmbeddedChunkDTO(
        document_id=doc_id,
        chunk_id=c_id,
        chunk_index=3,
        content="Archival excerpt from the War for the Union.",
        page_number=12,
        token_count=8,
        embedding=dummy_vec,
        embedding_model="mock-feature-hash-v1",
        embedding_model_version="1.0.0",
    )

    assert chunk_dto.document_id == doc_id
    assert chunk_dto.chunk_id == c_id
    assert chunk_dto.chunk_index == 3
    assert chunk_dto.content == "Archival excerpt from the War for the Union."
    assert chunk_dto.page_number == 12
    assert chunk_dto.embedding == dummy_vec
    assert chunk_dto.embedding_model == "mock-feature-hash-v1"
    assert chunk_dto.embedding_model_version == "1.0.0"

    d = chunk_dto.to_dict()
    assert d["document_id"] == str(doc_id)
    assert d["chunk_id"] == str(c_id)
    assert d["chunk_index"] == 3
    assert d["content"] == "Archival excerpt from the War for the Union."
    assert d["page_number"] == 12
    assert d["embedding_model"] == "mock-feature-hash-v1"
    assert d["embedding_model_version"] == "1.0.0"
    assert len(d["embedding"]) == 384

    res = chunk_dto.to_search_result(similarity=0.94)
    assert res["similarity"] == 0.94
    assert res["chunk_id"] == str(c_id)
    assert res["page_number"] == 12


# ---------------------------------------------------------------------------
# 4. Chunk Repository & pgvector Simulation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chunk_repository_save_and_retrieve():
    doc_id = uuid.uuid4()
    mock_session = AsyncMock()
    added_entities = []

    def mock_add(entity):
        added_entities.append(entity)

    mock_session.add = MagicMock(side_effect=mock_add)
    mock_session.flush = AsyncMock()

    repo = ChunkRepository(mock_session)

    raw_chunks = [
        ChunkDTO(chunk_index=0, content="First historical paragraph", page_number=1, token_count=3),
        ChunkDTO(chunk_index=1, content="Second historical paragraph", page_number=2, token_count=3),
    ]
    provider = MockEmbeddingProvider(dimension=384)
    embeddings = await provider.embed_texts([c.content for c in raw_chunks])

    embedded_dtos = await repo.save_chunks_and_embeddings(
        document_id=doc_id,
        chunks=raw_chunks,
        embeddings=embeddings,
        model_name=provider.model_name,
        model_version=provider.model_version,
        dimension=provider.dimension,
    )

    # Verify return values
    assert len(embedded_dtos) == 2
    for i, dto in enumerate(embedded_dtos):
        assert dto.document_id == doc_id
        assert dto.chunk_index == i
        assert dto.page_number == i + 1
        assert len(dto.embedding) == 384
        assert dto.embedding_model == "mock-feature-hash-v1"
        assert dto.embedding_model_version == "1.0.0"

    # Verify session added both DocumentChunk and ChunkEmbedding entities
    chunks_added = [e for e in added_entities if isinstance(e, DocumentChunk)]
    embeddings_added = [e for e in added_entities if isinstance(e, ChunkEmbedding)]
    assert len(chunks_added) == 2
    assert len(embeddings_added) == 2
    assert embeddings_added[0].chunk_id == chunks_added[0].id
    assert embeddings_added[0].model_name == "mock-feature-hash-v1"
    assert embeddings_added[0].is_active is True


@pytest.mark.asyncio
async def test_chunk_repository_similarity_search_ranking():
    doc_id = uuid.uuid4()
    provider = MockEmbeddingProvider(dimension=384)

    # Texts with distinct semantic content
    c1_text = "The Battle of Gettysburg was fought July 1 to July 3 1863 in Pennsylvania"
    c2_text = "Maritime naval blockades during the Civil War in Charleston harbor"
    c3_text = "Agricultural economic conditions and cotton production in 1860"

    v1 = await provider.embed_text(c1_text)
    v2 = await provider.embed_text(c2_text)
    v3 = await provider.embed_text(c3_text)

    chunk1 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=0, content=c1_text, page_number=1)
    chunk2 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=1, content=c2_text, page_number=2)
    chunk3 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=2, content=c3_text, page_number=3)

    emb1 = ChunkEmbedding(id=uuid.uuid4(), chunk_id=chunk1.id, model_name="mock-feature-hash-v1", model_version="1.0", embedding=v1, is_active=True)
    emb2 = ChunkEmbedding(id=uuid.uuid4(), chunk_id=chunk2.id, model_name="mock-feature-hash-v1", model_version="1.0", embedding=v2, is_active=True)
    emb3 = ChunkEmbedding(id=uuid.uuid4(), chunk_id=chunk3.id, model_name="mock-feature-hash-v1", model_version="1.0", embedding=v3, is_active=True)

    doc = Document(id=doc_id, title="Civil War Compendium", source="loc", record_type="document")

    # Mock execute returning all 3 chunk pairs
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        (chunk1, emb1, doc),
        (chunk2, emb2, doc),
        (chunk3, emb3, doc),
    ]
    mock_session.execute.return_value = mock_result

    repo = ChunkRepository(mock_session)

    # Query specifically about Gettysburg
    query = "Gettysburg battle Pennsylvania 1863"
    query_vector = await provider.embed_text(query)

    results = await repo._in_memory_similarity_search(query_vector=query_vector, limit=3)
    assert len(results) == 3
    # Top ranked chunk must be chunk 1 (Gettysburg)
    assert results[0]["chunk_id"] == chunk1.id
    assert "Gettysburg" in results[0]["content"]
    assert results[0]["similarity"] > results[1]["similarity"]
    assert results[0]["similarity"] > results[2]["similarity"]
    assert results[0]["title"] == "Civil War Compendium"
    assert results[0]["source"] == "loc"


# ---------------------------------------------------------------------------
# 5. Embedding Pipeline Service Orchestrator Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_embedding_pipeline_service_flow():
    doc_id = uuid.uuid4()
    mock_session = AsyncMock()
    added_entities = []

    def mock_add(entity):
        added_entities.append(entity)

    mock_session.add = MagicMock(side_effect=mock_add)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    provider = MockEmbeddingProvider(dimension=384)
    chunker = TextChunker()
    service = EmbeddingPipelineService(
        session=mock_session,
        embedding_provider=provider,
        chunker=chunker,
    )

    raw_text = (
        "Speeches of Abraham Lincoln in Ohio.\n\n"
        "Delivered at Columbus, Ohio, September 1859.\n\n"
        "Fellow-citizens: I appear before you today to discuss the great principles of liberty."
    )
    content = ExtractedContent(
        pages=[ExtractedPage(page_number=1, text=raw_text)],
        total_pages=1,
        full_text=raw_text,
    )

    # 1. Test clean text & chunking
    chunks = service.create_chunks(content, max_tokens=40, overlap=5)
    assert len(chunks) >= 1
    for c in chunks:
        assert isinstance(c, ChunkDTO)

    # 2. Test embedding generation
    embeddings = await service.generate_embeddings(chunks)
    assert len(embeddings) == len(chunks)
    assert len(embeddings[0]) == 384

    # 3. Test full pipeline execution
    embedded_chunks = await service.process_document_embeddings(
        document_id=doc_id,
        content=content,
        max_tokens=40,
        overlap=5,
    )

    assert len(embedded_chunks) == len(chunks)
    assert mock_session.commit.called
    for ec in embedded_chunks:
        assert ec.document_id == doc_id
        assert ec.embedding_model == "mock-feature-hash-v1"
        assert len(ec.embedding) == 384


# ---------------------------------------------------------------------------
# 6. Real Prototype Dataset Verification Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_prototype_pdf_embedding_and_similarity():
    """Verify embedding pipeline with real prototype PDF: warforunion00beec.pdf"""
    assert PDF_PATH.exists(), f"Missing real prototype PDF at {PDF_PATH}"

    # Step 1: Process real PDF using PDFProcessor
    processor = PDFProcessor()
    result = await processor.process(PDF_PATH)
    assert result.total_pages > 0

    # Step 2: Build ExtractedContent from real extracted pages
    pages = [
        ExtractedPage(
            page_number=p.page_number,
            text=p.text,
            word_count=p.word_count,
        )
        for p in result.pages
        if p.text and p.text.strip()
    ]
    content = ExtractedContent(
        pages=pages[:5],  # Use first 5 real pages for fast focused test
        total_pages=len(pages[:5]),
        full_text="\n\n".join(p.text for p in pages[:5]),
    )

    doc_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    # Step 3: Run real content through EmbeddingPipelineService
    provider = MockEmbeddingProvider(dimension=384)
    service = EmbeddingPipelineService(
        session=mock_session,
        embedding_provider=provider,
        chunker=TextChunker(),
    )

    embedded_chunks = await service.process_document_embeddings(
        document_id=doc_id,
        content=content,
        max_tokens=100,
        overlap=15,
    )

    assert len(embedded_chunks) > 0
    # Verify retention of all 8 fields on real data chunks
    for chunk in embedded_chunks:
        assert chunk.document_id == doc_id
        assert chunk.chunk_id is not None
        assert isinstance(chunk.chunk_index, int)
        assert len(chunk.content.strip()) > 0
        assert chunk.page_number is not None
        assert len(chunk.embedding) == 384
        assert chunk.embedding_model == "mock-feature-hash-v1"
        assert chunk.embedding_model_version is not None

    # Step 4: Verify similarity search on the real chunks
    doc = Document(id=doc_id, title="War for the Union by Henry Ward Beecher", source="internet_archive")
    mock_result = MagicMock()
    # Mock retrieval of the generated chunks for similarity search
    mock_rows = [
        (
            DocumentChunk(
                id=c.chunk_id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                content=c.content,
                page_number=c.page_number,
            ),
            ChunkEmbedding(
                id=uuid.uuid4(),
                chunk_id=c.chunk_id,
                model_name=c.embedding_model,
                model_version=c.embedding_model_version,
                embedding=c.embedding,
                is_active=True,
            ),
            doc,
        )
        for c in embedded_chunks
    ]
    mock_result.all.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    # Search query
    query = "war union speech Henry Ward Beecher"
    search_matches = await service.similarity_search(query=query, limit=3)
    assert len(search_matches) > 0
    top = search_matches[0]
    assert top["document_id"] == doc_id
    assert top["similarity"] > 0.0
    assert "war" in top["content"].lower() or "union" in top["content"].lower() or "speech" in top["content"].lower()


@pytest.mark.asyncio
async def test_real_prototype_text_embedding_and_similarity():
    """Verify embedding pipeline with real prototype text: thelifeandpublic22681gut.txt"""
    assert TEXT_PATH.exists(), f"Missing real prototype text at {TEXT_PATH}"

    # Step 1: Process real text file using TextProcessor
    processor = TextProcessor()
    result = await processor.process(TEXT_PATH)
    assert result.extracted_text is not None

    # Step 2: Use sample excerpt from real Lincoln biography
    excerpt = result.extracted_text[:3000]
    content = ExtractedContent(
        pages=[ExtractedPage(page_number=1, text=excerpt)],
        total_pages=1,
        full_text=excerpt,
    )

    doc_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    provider = MockEmbeddingProvider(dimension=384)
    service = EmbeddingPipelineService(
        session=mock_session,
        embedding_provider=provider,
        chunker=TextChunker(),
    )

    embedded_chunks = await service.process_document_embeddings(
        document_id=doc_id,
        content=content,
        max_tokens=80,
        overlap=10,
    )

    assert len(embedded_chunks) >= 2

    # Step 3: Verify similarity search on Lincoln biography chunks
    doc = Document(id=doc_id, title="Life and Public Services of Abraham Lincoln", source="internet_archive")
    mock_result = MagicMock()
    mock_rows = [
        (
            DocumentChunk(
                id=c.chunk_id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                content=c.content,
                page_number=c.page_number,
            ),
            ChunkEmbedding(
                id=uuid.uuid4(),
                chunk_id=c.chunk_id,
                model_name=c.embedding_model,
                model_version=c.embedding_model_version,
                embedding=c.embedding,
                is_active=True,
            ),
            doc,
        )
        for c in embedded_chunks
    ]
    mock_result.all.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    search_matches = await service.similarity_search(query="Abraham Lincoln president services", limit=3)
    assert len(search_matches) > 0
    top = search_matches[0]
    assert top["similarity"] > 0.0
    assert "lincoln" in top["content"].lower() or "abraham" in top["content"].lower()
