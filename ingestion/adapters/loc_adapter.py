import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from backend.app.core.exceptions import (
    SourceAPIError,
    SourceMediaDownloadError,
    SourceRecordNotFoundError,
    SourceUnavailableError,
)
from ingestion.adapters.base import SourceAdapter
from ingestion.models.canonical import (
    CanonicalArchiveRecord,
    SearchPage,
    SourceRawRecord,
    SourceSearchResult,
)
from ingestion.normalizers.loc_normalizer import LibraryOfCongressNormalizer

logger = logging.getLogger(__name__)


class LibraryOfCongressAdapter(SourceAdapter):
    """
    Production adapter for the Library of Congress (LOC) API.
    LOC provides open programmatic access to historical books, manuscripts, photographs, and newspapers.
    Base search URL: https://www.loc.gov/search/?fo=json
    """

    BASE_URL = "https://www.loc.gov"

    def __init__(self, normalizer: Optional[LibraryOfCongressNormalizer] = None):
        self._normalizer = normalizer or LibraryOfCongressNormalizer()

    @property
    def source_name(self) -> str:
        return "library_of_congress"

    @property
    def adapter_version(self) -> str:
        return self._normalizer.ADAPTER_VERSION

    async def search(
        self, query: str, limit: int = 10, cursor: Optional[str] = None
    ) -> SearchPage:
        page = int(cursor) if cursor and cursor.isdigit() else 1
        url = f"{self.BASE_URL}/search/"
        params = {
            "fo": "json",
            "q": query,
            "c": limit,
            "sp": page,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    return SearchPage(results=[], next_cursor=None, total_count=0)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as e:
            raise SourceUnavailableError(
                f"Library of Congress API is currently unreachable at {url}: {e}",
                details={"source": self.source_name, "query": query, "url": url},
            ) from e
        except httpx.TimeoutException as e:
            raise SourceUnavailableError(
                f"Library of Congress API timed out for query '{query}': {e}",
                details={"source": self.source_name, "query": query, "url": url},
            ) from e
        except httpx.HTTPStatusError as e:
            raise SourceAPIError(
                f"Library of Congress API returned error HTTP {e.response.status_code}: {e}",
                details={"source": self.source_name, "status_code": e.response.status_code, "url": url},
            ) from e
        except Exception as e:
            raise SourceAPIError(
                f"Unexpected error querying Library of Congress API: {e}",
                details={"source": self.source_name, "query": query, "error": str(e)},
            ) from e

        results: List[SourceSearchResult] = []
        raw_items = data.get("results", [])
        for item in raw_items:
            item_id = str(item.get("id") or item.get("item", {}).get("id") or "")
            title_val = item.get("title", "Untitled Historical Document")
            title = title_val[0] if isinstance(title_val, list) and title_val else str(title_val)

            description = ""
            if item.get("description"):
                desc_val = item["description"]
                description = desc_val[0] if isinstance(desc_val, list) and desc_val else str(desc_val)
            elif item.get("notes"):
                notes_val = item["notes"]
                description = " ".join([str(n) for n in notes_val[:2]]) if isinstance(notes_val, list) else str(notes_val)

            date = ""
            if item.get("date"):
                d_val = item["date"]
                date = d_val[0] if isinstance(d_val, list) and d_val else str(d_val)

            image_url = ""
            if item.get("image_url"):
                img_val = item["image_url"]
                image_url = img_val[0] if isinstance(img_val, list) and img_val else str(img_val)

            # Extract media resource URL (PDF or high-res document image)
            media_url = image_url
            for link in item.get("resources", []):
                for file_info in link.get("files", []):
                    if isinstance(file_info, list):
                        for f in file_info:
                            if isinstance(f, dict) and f.get("url", "").endswith(".pdf"):
                                media_url = f["url"]
                                break

            results.append(
                SourceSearchResult(
                    source=self.source_name,
                    source_id=item_id,
                    title=title,
                    description=description,
                    date=date,
                    media_url=media_url or image_url,
                    thumbnail_url=image_url,
                    record_type="document",
                )
            )

        pagination = data.get("pagination", {})
        total = pagination.get("total")
        next_page = str(page + 1) if pagination.get("next") else None

        return SearchPage(results=results, next_cursor=next_page, total_count=total)

    async def fetch_record(self, source_id: str) -> SourceRawRecord:
        url = source_id if source_id.startswith("http") else f"{self.BASE_URL}/item/{source_id}/"
        params = {"fo": "json"}

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    raise SourceRecordNotFoundError(
                        f"Record '{source_id}' not found in Library of Congress repository at {url}.",
                        details={"source": self.source_name, "source_id": source_id, "url": url},
                    )
                resp.raise_for_status()
                data = resp.json()
                return SourceRawRecord(
                    source=self.source_name,
                    source_id=source_id,
                    raw_data=data,
                    source_url=url,
                )
        except (SourceRecordNotFoundError, SourceUnavailableError, SourceAPIError):
            raise
        except httpx.ConnectError as e:
            raise SourceUnavailableError(
                f"Library of Congress service unreachable while fetching record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "url": url},
            ) from e
        except httpx.TimeoutException as e:
            raise SourceUnavailableError(
                f"Library of Congress request timed out fetching record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "url": url},
            ) from e
        except httpx.HTTPStatusError as e:
            raise SourceAPIError(
                f"Library of Congress returned HTTP {e.response.status_code} for record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise SourceAPIError(
                f"Failed to retrieve record '{source_id}' from Library of Congress: {e}",
                details={"source": self.source_name, "source_id": source_id, "error": str(e)},
            ) from e

    async def download_media(self, media_url: str) -> AsyncIterator[bytes]:
        if not media_url or not media_url.startswith("http"):
            raise SourceMediaDownloadError(
                f"Cannot download media with invalid URL: '{media_url}'",
                details={"source": self.source_name, "media_url": media_url},
            )

        async def stream_generator():
            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    async with client.stream("GET", media_url) as resp:
                        if resp.status_code == 404:
                            raise SourceMediaDownloadError(
                                f"Digital media asset not found at {media_url}",
                                details={"source": self.source_name, "media_url": media_url, "status_code": 404},
                            )
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                            yield chunk
            except SourceMediaDownloadError:
                raise
            except httpx.ConnectError as e:
                raise SourceUnavailableError(
                    f"Library of Congress media server unreachable at {media_url}: {e}",
                    details={"source": self.source_name, "media_url": media_url},
                ) from e
            except httpx.HTTPStatusError as e:
                raise SourceMediaDownloadError(
                    f"Failed downloading media asset from {media_url} (HTTP {e.response.status_code}): {e}",
                    details={"source": self.source_name, "media_url": media_url, "status_code": e.response.status_code},
                ) from e
            except Exception as e:
                raise SourceMediaDownloadError(
                    f"Failed downloading media asset from {media_url}: {e}",
                    details={"source": self.source_name, "media_url": media_url, "error": str(e)},
                ) from e

        return stream_generator()

    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        return self._normalizer.normalize(raw_record)
