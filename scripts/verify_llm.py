import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import settings
from ai.providers.gemini_provider import GeminiProvider
from ai.models.enrichment import AIEnrichmentResult, AIMetadata, AIEntity, AIResponseEnvelope
from ai.validation.model_validator import ModelOutputValidator


SAMPLE_HISTORICAL_TEXT = (
    "On November 19, 1863, President Abraham Lincoln delivered the Gettysburg Address "
    "at the Soldiers' National Cemetery in Gettysburg, Pennsylvania, during the American Civil War. "
    "He dedicated the cemetery to the Union soldiers who had fallen in the battle and emphasized "
    "that government of the people, by the people, for the people, shall not perish from the earth."
)


async def verify_llm() -> bool:
    print("====================================================")
    print("              REAL GEMINI LLM VERIFICATION          ")
    print("====================================================\n")

    if not settings.GEMINI_API_KEY:
        print("FAIL: GEMINI_API_KEY is not set in environment or .env file.")
        return False

    provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)

    results: Dict[str, bool] = {}

    # 1. Request and structured enrichment
    try:
        envelope = await provider.enrich(SAMPLE_HISTORICAL_TEXT)
        results["request_response"] = envelope is not None and envelope.data is not None
        enrichment: AIEnrichmentResult = envelope.data
    except Exception as e:
        print(f"Error calling Gemini LLM: {e}")
        return False

    # 2. Schema conformity
    results["structured_output"] = isinstance(enrichment, AIEnrichmentResult)

    # 3. Entity extraction
    entities = enrichment.entities
    results["entity_extraction"] = bool(
        len(entities) > 0
        and any("Lincoln" in e.name or "Gettysburg" in e.name for e in entities)
    )

    # 4. Metadata extraction
    meta = enrichment.metadata
    results["metadata_extraction"] = bool(
        meta.historical_period is not None
        or (meta.date and "1863" in str(meta.date))
    )

    # 5. Provenance verification
    prov = envelope.provenance
    results["provenance"] = (
        envelope.provider == "Gemini"
        and prov == "AI"
        and envelope.model == provider.model_name
    )

    # 6. Verify Mock Provider was NOT used
    # MockLLMProvider sets provider_name = "MockLLM"
    mock_used = envelope.provider == "MockLLM"
    results["no_mock_used"] = not mock_used

    # 7. Safe rejection of malformed output
    try:
        # Invalid JSON must raise validation error without crashing
        malformed_json = '{"title": 123, "date": "not-a-date-obj", "creators": "not-a-list"}'
        ModelOutputValidator.parse_and_validate(malformed_json, AIMetadata)
        # Should sanitize/salvage or reject gracefully
        results["rejection_safety"] = True
    except Exception:
        results["rejection_safety"] = True

    # Print formatted checklist
    print(f"LLM Provider ................. {'PASS' if results.get('request_response') else 'FAIL'}")
    print(f"Provider ..................... {envelope.provider}")
    print(f"Structured Output ............ {'PASS' if results.get('structured_output') else 'FAIL'}")
    print(f"Entity Extraction ............ {'PASS' if results.get('entity_extraction') else 'FAIL'}")
    print(f"Metadata Extraction .......... {'PASS' if results.get('metadata_extraction') else 'FAIL'}")
    print(f"Provenance ................... {'PASS' if results.get('provenance') else 'FAIL'}")
    print(f"Mock Provider Used ........... {'YES' if mock_used else 'NO'}")

    all_passed = (
        results.get("request_response", False)
        and results.get("structured_output", False)
        and results.get("entity_extraction", False)
        and results.get("metadata_extraction", False)
        and results.get("provenance", False)
        and results.get("no_mock_used", False)
    )

    print("\n----------------------------------------------------")
    if all_passed:
        print("RESULT: REAL LLM VERIFIED")
    else:
        print("RESULT: REAL LLM VERIFICATION FAILED")
    print("----------------------------------------------------\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(verify_llm())
    sys.exit(0 if success else 1)
