import asyncio
import sys
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def search_ia_more():
    url = "https://archive.org/advancedsearch.php"
    
    searches = [
        ("video", "title:(Gandhi OR \"Indian Independence\") AND mediatype:movies"),
        ("audio", "title:(Gandhi OR Nehru OR \"All India Radio\") AND mediatype:audio"),
        ("manuscript/book", "title:(\"Tagore\" OR \"Constitution of India\" OR \"Ashoka\" OR \"Sanskrit\") AND mediatype:texts"),
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for cat, q in searches:
            params = {
                "q": q,
                "fl[]": ["identifier", "title", "mediatype", "year"],
                "rows": 4,
                "output": "json",
            }
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                docs = data.get("response", {}).get("docs", [])
                print(f"\n=== {cat.upper()} ===")
                for d in docs:
                    print(f"  ID: {d.get('identifier')} | Title: {d.get('title', '')[:55]} | Year: {d.get('year')}")
            except Exception as e:
                print(f"Error {cat}:", e)

asyncio.run(search_ia_more())
