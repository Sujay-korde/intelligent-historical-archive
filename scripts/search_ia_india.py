import asyncio
import sys
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def search_ia():
    url = "https://archive.org/advancedsearch.php"
    
    # 1. Indian Historical Audio
    # 2. Indian Manuscript / Constitution
    # 3. Indian Historical Map
    # 4. Indian Historical Video
    searches = [
        ("audio", "title:(Nehru OR Tagore) AND mediatype:audio"),
        ("video", "title:(India Independence OR Gandhi) AND mediatype:movies"),
        ("manuscript", "collection:(digitallibraryofindia) AND title:(History of India)"),
        ("map", "title:(Map of India) AND mediatype:image"),
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for cat, q in searches:
            params = {
                "q": q,
                "fl[]": ["identifier", "title", "mediatype", "year"],
                "rows": 3,
                "output": "json",
            }
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                docs = data.get("response", {}).get("docs", [])
                print(f"\n=== {cat.upper()} ({len(docs)} found) ===")
                for d in docs:
                    print(f"  ID: {d.get('identifier')} | Title: {d.get('title', '')[:50]} | Year: {d.get('year')}")
            except Exception as e:
                print(f"Error {cat}:", e)

asyncio.run(search_ia())
