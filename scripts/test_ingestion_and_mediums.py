import hashlib
import json
import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000/api/v1"

def test_deduplication():
    print("\n--- 1. Testing Pre-Ingestion Deduplication Gate ---")
    
    # Test Existing Record (from initial 45 items)
    existing_id = "Swaraj-Gandhi-1948-01-11"
    resp = httpx.post(f"{API_BASE}/ingest/validate", json={
        "source": "internet_archive",
        "source_id": existing_id
    }, timeout=10.0)
    print(f"Validation for existing item '{existing_id}':")
    data = resp.json()
    print(f"  Status: {resp.status_code}, is_duplicate: {data.get('is_duplicate')}")
    print(f"  Message: {data.get('message')}")
    assert data.get("is_duplicate") is True, "Expected existing record to be flagged as duplicate!"

    # Test New Record (1838 Bengal & Awadh Map)
    new_id = "dr_composite-map-a-map-of-bengal-bahar-oude--allahabad-with-part-of-agra-13170043"
    resp = httpx.post(f"{API_BASE}/ingest/validate", json={
        "source": "internet_archive",
        "source_id": new_id
    }, timeout=10.0)
    print(f"\nValidation for new item '{new_id}':")
    data = resp.json()
    print(f"  Status: {resp.status_code}, is_duplicate: {data.get('is_duplicate')}")
    print(f"  Message: {data.get('message')}")
    assert data.get("is_duplicate") is False, "Expected new record to be marked unique!"


def test_researcher_upload_and_deduplication():
    print("\n--- 2. Testing Local Historical Artifact Deposit & SHA-256 Gate ---")
    
    # Sample historical Indian artifact content
    manuscript_content = (
        "THE CONSTITUTION OF INDIA (PREAMBLE)\n"
        "WE, THE PEOPLE OF INDIA, having solemnly resolved to constitute India into a "
        "SOVEREIGN SOCIALIST SECULAR DEMOCRATIC REPUBLIC and to secure to all its citizens: "
        "JUSTICE, social, economic and political; LIBERTY of thought, expression, belief, faith and worship; "
        "EQUALITY of status and of opportunity; and to promote among them all FRATERNITY "
        "assuring the dignity of the individual and the unity and integrity of the Nation;\n"
        "IN OUR CONSTITUENT ASSEMBLY this twenty-sixth day of November, 1949, do HEREBY ADOPT, "
        "ENACT AND GIVE TO OURSELVES THIS CONSTITUTION.\n"
        "Signatories include Dr. B.R. Ambedkar, Jawaharlal Nehru, Sardar Vallabhbhai Patel, and Dr. Rajendra Prasad."
    ).encode("utf-8")

    file_hash = hashlib.sha256(manuscript_content).hexdigest()
    print(f"Computed Artifact SHA-256: {file_hash}")

    # Check pre-flight validation by SHA-256
    val_resp = httpx.post(f"{API_BASE}/ingest/validate", json={"sha256": file_hash}, timeout=10.0)
    print(f"Pre-flight hash check: is_duplicate={val_resp.json().get('is_duplicate')}")

    # Upload artifact
    files = {"file": ("constitution_preamble_1949.txt", manuscript_content, "text/plain")}
    form_data = {
        "title": "1949 Constitution of India Preamble & Constituent Assembly Proclamation",
        "creator": "Dr. B.R. Ambedkar & Constituent Assembly of India",
        "date_raw": "November 26, 1949",
        "record_type": "manuscript",
        "language": "English / Hindi",
        "description": "Original calligraphic preamble and resolution adopting the Constitution of the Republic of India at New Delhi.",
    }

    print("Submitting researcher deposit to /api/v1/ingest/upload...")
    up_resp = httpx.post(f"{API_BASE}/ingest/upload", data=form_data, files=files, timeout=60.0)
    print(f"Upload response status: {up_resp.status_code}")
    up_data = up_resp.json()
    print("Ingest Result:")
    print(f"  Document ID: {up_data.get('document_id')}")
    print(f"  Title: {up_data.get('title')}")
    print(f"  Record Type: {up_data.get('record_type')}")
    print(f"  Chunks count: {up_data.get('chunks_count')}")
    print(f"  Entities count: {up_data.get('entities_count')}")
    print(f"  Quality score: {up_data.get('quality_score')}")
    print(f"  Message: {up_data.get('message')}")

    # Now attempt duplicate upload of the exact same artifact
    print("\nAttempting duplicate upload of the same physical file...")
    files2 = {"file": ("constitution_preamble_1949.txt", manuscript_content, "text/plain")}
    dup_resp = httpx.post(f"{API_BASE}/ingest/upload", data=form_data, files=files2, timeout=20.0)
    dup_data = dup_resp.json()
    print(f"Duplicate upload status: {dup_resp.status_code}")
    print(f"  is_duplicate: {dup_data.get('is_duplicate')}")
    print(f"  existing_document_id: {dup_data.get('document_id')}")
    print(f"  message: {dup_data.get('message')}")
    assert dup_data.get("is_duplicate") is True, "Duplicate upload was not caught by SHA-256 gate!"
    print("[SUCCESS] SHA-256 deduplication gate successfully prevented duplicate preservation.")


def test_external_ingest_indian_record():
    print("\n--- 3. Testing Real External Ingestion: Indian Historical Map (1838 Bengal & Awadh) ---")
    source_id = "dr_composite-map-a-map-of-bengal-bahar-oude--allahabad-with-part-of-agra-13170043"
    payload = {
        "source": "internet_archive",
        "source_id": source_id,
        "record_type": "map"
    }

    print(f"Calling POST /api/v1/ingest/external for '{source_id}'...")
    resp = httpx.post(f"{API_BASE}/ingest/external", json=payload, timeout=90.0)
    print(f"External Ingest response status: {resp.status_code}")
    data = resp.json()
    print("Ingest Result:")
    print(f"  is_duplicate: {data.get('is_duplicate')}")
    print(f"  document_id: {data.get('document_id')}")
    print(f"  title: {data.get('title')}")
    print(f"  status: {data.get('status')}")
    print(f"  processing_stage: {data.get('processing_stage')}")
    print(f"  chunks_count: {data.get('chunks_count')}")
    print(f"  entities_count: {data.get('entities_count')}")
    print(f"  quality_score: {data.get('quality_score')}")
    print(f"  message: {data.get('message')}")

    # Now verify re-ingestion deduplication gate:
    print(f"\nAttempting re-ingestion of '{source_id}'...")
    re_resp = httpx.post(f"{API_BASE}/ingest/external", json=payload, timeout=20.0)
    re_data = re_resp.json()
    print(f"Re-ingest status: {re_resp.status_code}")
    print(f"  is_duplicate: {re_data.get('is_duplicate')}")
    print(f"  message: {re_data.get('message')}")
    assert re_data.get("is_duplicate") is True, "Expected re-ingestion to be intercepted by deduplication gate!"
    print("[SUCCESS] External repository deduplication gate verified.")


if __name__ == "__main__":
    test_deduplication()
    test_researcher_upload_and_deduplication()
    test_external_ingest_indian_record()

