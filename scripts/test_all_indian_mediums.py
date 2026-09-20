import hashlib
import json
import sys
from pathlib import Path
import httpx

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000/api/v1"

def deposit_and_verify_medium(file_path: Path, title: str, creator: str, date_raw: str, record_type: str, description: str):
    print(f"\n=======================================================")
    print(f"DEPOSITING & TESTING MEDIUM: [{record_type.upper()}]")
    print(f"File: {file_path.name} ({file_path.stat().st_size} bytes)")
    print(f"Title: {title}")
    print(f"=======================================================")

    content = file_path.read_bytes()
    file_hash = hashlib.sha256(content).hexdigest()
    print(f"Artifact SHA-256: {file_hash}")

    # 1. Pre-validation
    val_resp = httpx.post(f"{API_BASE}/ingest/validate", json={"sha256": file_hash}, timeout=10.0)
    print(f"Pre-flight Deduplication Check: is_duplicate={val_resp.json().get('is_duplicate')}")

    # 2. Upload and Ingestion
    mime_type = "video/mp4" if record_type == "video" else "audio/mpeg" if record_type == "audio" else "application/octet-stream"
    files = {"file": (file_path.name, content, mime_type)}
    data = {
        "title": title,
        "creator": creator,
        "date_raw": date_raw,
        "record_type": record_type,
        "language": "English / Hindi",
        "description": description,
    }

    print("Uploading file to /api/v1/ingest/upload...")
    up_resp = httpx.post(f"{API_BASE}/ingest/upload", data=data, files=files, timeout=60.0)
    print(f"Upload HTTP Status: {up_resp.status_code}")
    res = up_resp.json()
    print("Ingestion Result:")
    doc_id = res.get("document_id")
    print(f"  Document ID: {doc_id}")
    print(f"  Status: {res.get('status')}")
    print(f"  Processing Stage: {res.get('processing_stage')}")
    print(f"  Chunks: {res.get('chunks_count')}")
    print(f"  Entities: {res.get('entities_count')}")
    print(f"  Quality Score: {res.get('quality_score')}")

    # 3. Test Deduplication Gate (re-upload exact file)
    print("Testing SHA-256 Deduplication Gate on re-upload...")
    files_dup = {"file": (file_path.name, content, mime_type)}
    dup_resp = httpx.post(f"{API_BASE}/ingest/upload", data=data, files=files_dup, timeout=20.0)
    dup_json = dup_resp.json()
    print(f"  Duplicate Detected: {dup_json.get('is_duplicate')}")
    print(f"  Existing Doc ID: {dup_json.get('document_id')}")
    assert dup_json.get("is_duplicate") is True, f"Deduplication failed for {record_type}!"
    print("  [SUCCESS] Deduplication gate blocked duplicate upload.")

    # 4. Fetch Document Details
    print(f"Fetching Document Details from /api/v1/documents/{doc_id}...")
    doc_resp = httpx.get(f"{API_BASE}/documents/{doc_id}", timeout=10.0)
    assert doc_resp.status_code == 200, f"Failed to fetch document details: {doc_resp.status_code}"
    doc_data = doc_resp.json()
    print(f"  Preserved Record Type: {doc_data.get('record_type')}")
    assets = doc_data.get("media_assets", [])
    print(f"  Media Assets Count: {len(assets)}")
    assert len(assets) > 0, "No media assets preserved!"
    primary_asset = assets[0]
    print(f"  Storage Key: {primary_asset.get('storage_key')}")
    print(f"  Media Type: {primary_asset.get('media_type')}")
    print(f"  MIME Type: {primary_asset.get('mime_type')}")
    print(f"  Access URL: {primary_asset.get('access_url')}")

    # 5. Stream Media Asset
    stream_url = f"http://127.0.0.1:8000{primary_asset.get('access_url')}"
    print(f"Streaming Media Asset from {stream_url}...")
    stream_resp = httpx.get(stream_url, timeout=15.0)
    print(f"  Stream HTTP Status: {stream_resp.status_code}")
    print(f"  Content-Type: {stream_resp.headers.get('content-type')}")
    print(f"  Accept-Ranges: {stream_resp.headers.get('accept-ranges')}")
    print(f"  Content-Length: {len(stream_resp.content)} bytes")
    assert stream_resp.status_code == 200, "Media stream failed!"
    assert len(stream_resp.content) == len(content), "Streamed content length mismatch!"
    print(f"  [SUCCESS] {record_type.capitalize()} stream verified perfectly.")
    return doc_id


if __name__ == "__main__":
    # Test Video
    video_path = Path("1947_indian_independence_newsreel.mp4")
    if video_path.exists():
        deposit_and_verify_medium(
            file_path=video_path,
            title="1947 Indian Independence Day Archival Newsreel & Flag Hoisting Ceremony",
            creator="Films Division of India",
            date_raw="August 15, 1947",
            record_type="video",
            description="Historical motion picture newsreel recording the transfer of power, midnight constituent assembly session, and first raising of the Indian national flag at Red Fort, New Delhi.",
        )

    # Test Audio
    audio_path = Path("1947_all_india_radio_announcement.mp3")
    if audio_path.exists():
        deposit_and_verify_medium(
            file_path=audio_path,
            title="1947 All India Radio Historic Midnight Broadcast Announcement",
            creator="All India Radio (AIR)",
            date_raw="August 14-15, 1947",
            record_type="audio",
            description="Historic All India Radio broadcast introducing Jawaharlal Nehru's Tryst with Destiny address to the sovereign Constituent Assembly of India.",
        )
