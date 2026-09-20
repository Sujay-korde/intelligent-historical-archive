import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.adapters.internet_archive_adapter import InternetArchiveAdapter

async def test_ids():
    adapter = InternetArchiveAdapter()
    candidates = [
        "hindswarajorindi00gand",           # Book / Manuscript: Hind Swaraj by Mahatma Gandhi
        "discoveryofindia00nehr",           # Historical Book: Discovery of India by Nehru
        "constitutionofind00indi",          # Historic Calligraphed Constitution of India
        "78_nehru-on-gandhis-death_jawaharlal-nehru_gbia7001460a",  # Audio: Nehru on Gandhi's Death
        "NehruSpeechTrystWithDestiny",       # Audio/Video: Tryst with Destiny
        "gov.archives.arc.1155106",         # Historic Film / Newsreel
        "1947-08-21_Free_India",            # Universal Newsreel 1947: Free India
        "dr_text-page-to-india-to-accompany-the-library-atlas-of-modern-geography-1892-0026265", # Map of India
    ]
    
    for cid in candidates:
        try:
            rec = await adapter.fetch_record(cid)
            norm = adapter.normalize(rec)
            print(f"[FOUND] {cid} | Type: {norm.record_type} | Media: {norm.media_type} | Title: {norm.title[:45]} | Assets: {len(norm.media_assets)}")
            if norm.media_assets:
                print(f"        Asset URL: {norm.media_assets[0].url[:60] if norm.media_assets[0].url else 'None'}")
        except Exception as e:
            print(f"[NOT FOUND/ERR] {cid}: {e}")

asyncio.run(test_ids())
