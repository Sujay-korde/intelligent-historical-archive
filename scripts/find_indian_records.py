import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter

async def find_records():
    adapter = InternetArchiveAdapter()
    
    queries = [
        ("audio", "title:(Nehru OR Gandhi OR Tagore) AND mediatype:audio"),
        ("video", "title:(India OR Gandhi OR Nehru) AND mediatype:movies"),
        ("manuscript", "title:(India manuscript OR \"Indian manuscript\" OR \"letter\" India) AND mediatype:texts"),
        ("map", "title:(India map OR \"map of India\") AND mediatype:image"),
    ]
    
    for medium, q in queries:
        print(f"\n--- Searching for {medium.upper()} ({q}) ---")
        try:
            page = await adapter.search(query=q, limit=4)
            for item in page.results:
                print(f"[{item.record_type}] ID: {item.source_id} | Title: {item.title[:60]}")
        except Exception as e:
            print("Error:", e)

asyncio.run(find_records())
