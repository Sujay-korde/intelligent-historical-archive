import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest

from ai.factory import create_enrichment_provider
from ai.interfaces.extractor import (
    AIEnrichmentProvider,
    EntityExtractor,
    MetadataExtractor,
    Summarizer,
)
from ai.models.enrichment import (
    AIEnrichmentResult,
    AIEntity,
    AIMetadata,
    AIResponseEnvelope,
    AISummary,
    EntityType,
)
from ai.providers.mock_provider import MockLLMProvider
from ai.services.enrichment_service import EnrichmentService
from ai.validation.model_validator import ModelOutputValidator
from backend.app.models.document import Document
from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.metadata import DocumentMetadata
from backend.app.models.relationship import Relationship


# --- 1. Model Output Validator Tests ---

def test_clean_json_markdown():
    raw_markdown = '```json\n{"title": "Gettysburg Address", "date": "1863"}\n```'
    clean = ModelOutputValidator.clean_json_markdown(raw_markdown)
    assert clean == '{"title": "Gettysburg Address", "date": "1863"}'

    conversational = 'Here is the JSON you requested:\n{"name": "Abraham Lincoln"}\nHope this helps!'
    clean2 = ModelOutputValidator.clean_json_markdown(conversational)
    assert clean2 == '{"name": "Abraham Lincoln"}'


def test_normalize_entity_type():
    assert ModelOutputValidator.normalize_entity_type("person") == EntityType.PERSON
    assert ModelOutputValidator.normalize_entity_type("per") == EntityType.PERSON
    assert ModelOutputValidator.normalize_entity_type("individual") == EntityType.PERSON
    assert ModelOutputValidator.normalize_entity_type("GPE") == EntityType.LOCATION
    assert ModelOutputValidator.normalize_entity_type("org") == EntityType.ORGANIZATION
    assert ModelOutputValidator.normalize_entity_type("battle") == EntityType.EVENT
    assert ModelOutputValidator.normalize_entity_type("year") == EntityType.DATE
    assert ModelOutputValidator.normalize_entity_type("random_unknown_type") == EntityType.TOPIC


def test_sanitize_entity():
    # Valid entity
    valid = ModelOutputValidator.sanitize_entity({
        "name": "Thomas Jefferson",
        "entity_type": "person",
        "confidence": 0.95,
        "description": "Third US President",
    })
    assert valid is not None
    assert valid.name == "Thomas Jefferson"
    assert valid.entity_type == EntityType.PERSON
    assert valid.confidence == 0.95

    # Clamping confidence out of range
    clamped = ModelOutputValidator.sanitize_entity({
        "name": "Continental Congress",
        "entity_type": "organization",
        "confidence": 1.5,
    })
    assert clamped is not None
    assert clamped.confidence == 1.0

    # Invalid empty name
    empty = ModelOutputValidator.sanitize_entity({"name": " ", "entity_type": "location"})
    assert empty is None


def test_sanitize_metadata():
    raw_data = {
        "title": "Declaration of Independence",
        "creator": "Thomas Jefferson",
        "date": "1776",
        "location": "Philadelphia",
        "organization": "Continental Congress",
        "document_type": "Declaration",
        "language": "English",
        "subjects": ["Liberty", "Independence"],
        "topics": ["American Revolution"],
        "historical_period": "Revolutionary Era",
        "confidence": 0.98,
    }
    meta = ModelOutputValidator.sanitize_metadata(raw_data)
    assert meta.title == "Declaration of Independence"
    assert meta.creator == "Thomas Jefferson"
    assert meta.date == "1776"
    assert meta.location == "Philadelphia"
    assert meta.organization == "Continental Congress"
    assert meta.document_type == "Declaration"
    assert meta.language == "English"
    assert meta.subjects == ["Liberty", "Independence"]
    assert meta.topics == ["American Revolution"]
    assert meta.historical_period == "Revolutionary Era"
    assert meta.confidence == 0.98


def test_parse_and_validate_full_enrichment():
    raw_json = """
    ```json
    {
        "metadata": {
            "title": "Speech on Slavery",
            "creator": "Frederick Douglass",
            "date": "1852",
            "historical_period": "Antebellum"
        },
        "entities": [
            {"name": "Frederick Douglass", "entity_type": "person", "confidence": 0.95},
            {"name": "Rochester", "entity_type": "place", "confidence": 0.90}
        ],
        "summary": {
            "summary": "Douglass delivers an address on American hypocrisy.",
            "key_points": ["Critique of American freedom", "Call for abolition"]
        }
    }
    ```
    """
    res = ModelOutputValidator.parse_and_validate(raw_json, AIEnrichmentResult)
    assert isinstance(res, AIEnrichmentResult)
    assert res.metadata.title == "Speech on Slavery"
    assert res.metadata.creator == "Frederick Douglass"
    assert len(res.entities) == 2
    assert res.entities[0].entity_type == EntityType.PERSON
    assert res.entities[1].entity_type == EntityType.LOCATION
    assert res.summary is not None
    assert "hypocrisy" in res.summary.summary
    assert len(res.summary.key_points) == 2


def test_malformed_llm_output_rejection():
    with pytest.raises(ValueError, match="Malformed JSON"):
        ModelOutputValidator.parse_and_validate("{broken_json: not valid}", AIEnrichmentResult)


# --- 2. Provider Interface & Provenance Tests ---

HISTORICAL_SAMPLE_TEXT = """
On July 4, 1852, Frederick Douglass delivered his famous address to the Rochester Ladies' Anti-Slavery Society
in Rochester, New York. In his oration, he examined the Declaration of Independence and the constitutional principles
of American liberty, speaking on the plight of millions enslaved in the South before the American Civil War.
"""


@pytest.mark.asyncio
async def test_mock_provider_metadata_extraction():
    provider = MockLLMProvider()
    assert isinstance(provider, MetadataExtractor)

    response = await provider.extract_metadata(HISTORICAL_SAMPLE_TEXT)
    assert isinstance(response, AIResponseEnvelope)
    assert response.provider == "MockLLM"
    assert response.model == "mock-historical-nlp-v1"
    assert response.provenance == "AI"
    assert response.confidence > 0.8
    assert response.data.language == "English"
    assert response.data.historical_period is not None


@pytest.mark.asyncio
async def test_mock_provider_entity_extraction():
    provider = MockLLMProvider()
    assert isinstance(provider, EntityExtractor)

    response = await provider.extract_entities(HISTORICAL_SAMPLE_TEXT)
    assert isinstance(response, AIResponseEnvelope)
    entities = response.data
    assert len(entities) > 0

    entity_types = {e.entity_type for e in entities}
    # Verify identification of requested entity types
    assert EntityType.PERSON in entity_types or EntityType.ORGANIZATION in entity_types or EntityType.LOCATION in entity_types
    assert EntityType.DATE in entity_types


@pytest.mark.asyncio
async def test_mock_provider_summarization():
    provider = MockLLMProvider()
    assert isinstance(provider, Summarizer)

    response = await provider.summarize(HISTORICAL_SAMPLE_TEXT, max_length=200)
    assert isinstance(response, AIResponseEnvelope)
    assert len(response.data.summary) <= 200
    assert len(response.data.key_points) > 0
    assert response.provenance == "AI"


@pytest.mark.asyncio
async def test_mock_provider_full_enrichment():
    provider = MockLLMProvider()
    assert isinstance(provider, AIEnrichmentProvider)

    response = await provider.enrich(HISTORICAL_SAMPLE_TEXT, context={"title": "Rochester Address"})
    assert isinstance(response, AIResponseEnvelope)
    assert response.data.metadata.title == "Rochester Address"
    assert response.data.metadata.historical_period is not None
    assert len(response.data.entities) > 0
    assert response.data.summary is not None
    assert response.provenance == "AI"
    assert isinstance(response.timestamp, datetime)


# --- 3. Source Metadata Preservation & Separate AI Storage ---

@pytest.mark.asyncio
async def test_enrichment_preserves_original_source_metadata():
    doc_id = uuid.uuid4()
    original_creators = [{"name": "Original Library Creator", "role": "Author"}]
    original_date_raw = "circa 1852"
    original_raw_metadata = {"source": "loc", "original_id": "loc_12345", "rights": "Public Domain"}

    doc_meta = DocumentMetadata(
        id=uuid.uuid4(),
        document_id=doc_id,
        creators=original_creators,
        date_raw=original_date_raw,
        language="English",
        subjects=["Civil War"],
        raw_metadata=original_raw_metadata,
        ai_metadata={},
        provenance=[],
    )

    mock_session = AsyncMock()
    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "document_metadata" in stmt_str:
            mock_result.scalar_one_or_none.return_value = doc_meta
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result
    mock_session.execute.side_effect = mock_execute
    mock_session.add = MagicMock()

    service = EnrichmentService(provider=MockLLMProvider())

    result = await service.enrich_and_persist(
        session=mock_session,
        document_id=doc_id,
        text=HISTORICAL_SAMPLE_TEXT,
    )

    # 1. Verify original source metadata is strictly preserved and untouched
    assert doc_meta.creators == original_creators
    assert doc_meta.date_raw == original_date_raw
    assert doc_meta.raw_metadata == original_raw_metadata

    # 2. Verify AI metadata is stored separately in ai_metadata
    assert doc_meta.ai_metadata is not None
    assert doc_meta.ai_metadata["provider"] == "MockLLM"
    assert doc_meta.ai_metadata["model"] == "mock-historical-nlp-v1"
    assert "summary" in doc_meta.ai_metadata
    assert "historical_period" in doc_meta.ai_metadata
    assert "topics" in doc_meta.ai_metadata

    # 3. Verify provenance audit trail was appended with AI provenance tag
    assert len(doc_meta.provenance) == 1
    assert doc_meta.provenance[0]["step"] == "ai_enrichment"
    assert doc_meta.provenance[0]["provenance"] == "AI"
    assert doc_meta.provenance[0]["provider"] == "MockLLM"


# --- 4. Resilient Fallback on Failure ---

@pytest.mark.asyncio
async def test_resilient_fallback_on_ai_failure():
    class FailingProvider(AIEnrichmentProvider):
        provider_name = "FailingAI"
        model_name = "failing-model"

        async def extract_metadata(self, text, context=None):
            raise ConnectionError("Simulated LLM API rate limit / outage")

        async def extract_entities(self, text, context=None):
            raise ConnectionError("Simulated LLM API rate limit / outage")

        async def summarize(self, text, max_length=300):
            raise ConnectionError("Simulated LLM API rate limit / outage")

        async def enrich(self, text, context=None):
            raise ConnectionError("Simulated LLM API rate limit / outage")

    service = EnrichmentService(provider=FailingProvider())

    # Ensure enrich_text does not raise an unhandled exception
    response = await service.enrich_text("Some historical text", context={"title": "Document Alpha"})
    assert isinstance(response, AIResponseEnvelope)
    assert response.confidence == 0.0
    assert response.provenance == "AI"
    assert response.data.metadata.title == "Document Alpha"
    assert "unavailable" in response.data.summary.summary.lower()


# --- 5. Factory Provider Creation ---

def test_factory_creation():
    provider = create_enrichment_provider(provider_type="mock")
    assert isinstance(provider, AIEnrichmentProvider)
    assert provider.provider_name == "MockLLM"

    # Gemini without API key should safely fall back to MockLLM
    gemini_fallback = create_enrichment_provider(provider_type="gemini", api_key="")
    assert isinstance(gemini_fallback, AIEnrichmentProvider)
    assert gemini_fallback.provider_name == "MockLLM"
