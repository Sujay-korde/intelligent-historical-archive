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
from ingestion.normalizers.ia_normalizer import InternetArchiveNormalizer

logger = logging.getLogger(__name__)


class InternetArchiveAdapter(SourceAdapter):
    """
    Production adapter for the Internet Archive (archive.org) API.
    Provides access to millions of digitized historical books, manuscripts, audio, and visual materials.
    """

    BASE_URL = "https://archive.org"
    SEARCH_URL = "https://archive.org/advancedsearch.php"
    METADATA_URL = "https://archive.org/metadata"

    def __init__(self, normalizer: Optional[InternetArchiveNormalizer] = None):
        self._normalizer = normalizer or InternetArchiveNormalizer()

    @property
    def source_name(self) -> str:
        return "internet_archive"

    @property
    def adapter_version(self) -> str:
        return self._normalizer.ADAPTER_VERSION

    async def search(
        self, query: str, limit: int = 10, cursor: Optional[str] = None
    ) -> SearchPage:
        page = int(cursor) if cursor and cursor.isdigit() else 1
        params = {
            "q": query,
            "fl[]": ["identifier", "title", "description", "creator", "date", "year", "mediatype"],
            "rows": limit,
            "page": page,
            "output": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(self.SEARCH_URL, params=params)
                if resp.status_code == 404:
                    return SearchPage(results=[], next_cursor=None, total_count=0)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as e:
            raise SourceUnavailableError(
                f"Internet Archive search service unreachable at {self.SEARCH_URL}: {e}",
                details={"source": self.source_name, "query": query, "url": self.SEARCH_URL},
            ) from e
        except httpx.TimeoutException as e:
            raise SourceUnavailableError(
                f"Internet Archive search query '{query}' timed out: {e}",
                details={"source": self.source_name, "query": query, "url": self.SEARCH_URL},
            ) from e
        except httpx.HTTPStatusError as e:
            raise SourceAPIError(
                f"Internet Archive search returned HTTP {e.response.status_code}: {e}",
                details={"source": self.source_name, "status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise SourceAPIError(
                f"Unexpected error querying Internet Archive API: {e}",
                details={"source": self.source_name, "query": query, "error": str(e)},
            ) from e

        response_block = data.get("response", {})
        docs = response_block.get("docs", [])
        total = response_block.get("numFound", len(docs))

        results: List[SourceSearchResult] = []
        for doc in docs:
            identifier = doc.get("identifier", "")
            title_val = doc.get("title", "Untitled Archive Item")
            title = title_val[0] if isinstance(title_val, list) and title_val else str(title_val)

            description = ""
            if doc.get("description"):
                desc_val = doc["description"]
                description = desc_val[0] if isinstance(desc_val, list) and desc_val else str(desc_val)

            date = str(doc.get("date") or doc.get("year") or "")
            mediatype = str(doc.get("mediatype") or "texts")
            media_url = f"{self.BASE_URL}/download/{identifier}/{identifier}.pdf"
            thumbnail_url = f"{self.BASE_URL}/services/img/{identifier}"

            results.append(
                SourceSearchResult(
                    source=self.source_name,
                    source_id=identifier,
                    title=title,
                    description=description,
                    date=date,
                    media_url=media_url,
                    thumbnail_url=thumbnail_url,
                    record_type="book" if mediatype == "texts" else "document",
                )
            )

        next_page = str(page + 1) if (page * limit) < total else None
        return SearchPage(results=results, next_cursor=next_page, total_count=total)

    async def fetch_record(self, source_id: str) -> SourceRawRecord:
        url = f"{self.METADATA_URL}/{source_id}"

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    raise SourceRecordNotFoundError(
                        f"Record '{source_id}' not found in Internet Archive repository at {url}.",
                        details={"source": self.source_name, "source_id": source_id, "url": url},
                    )
                resp.raise_for_status()
                data = resp.json()

                # Archive.org returns empty json `{}` when an item does not exist
                if not data or not data.get("metadata"):
                    raise SourceRecordNotFoundError(
                        f"Record '{source_id}' contains no metadata or does not exist in Internet Archive.",
                        details={"source": self.source_name, "source_id": source_id},
                    )

                return SourceRawRecord(
                    source=self.source_name,
                    source_id=source_id,
                    raw_data=data,
                    source_url=f"{self.BASE_URL}/details/{source_id}",
                )
        except (SourceRecordNotFoundError, SourceUnavailableError, SourceAPIError):
            raise
        except httpx.ConnectError as e:
            raise SourceUnavailableError(
                f"Internet Archive metadata service unreachable for record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "url": url},
            ) from e
        except httpx.TimeoutException as e:
            raise SourceUnavailableError(
                f"Internet Archive request timed out fetching record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "url": url},
            ) from e
        except httpx.HTTPStatusError as e:
            raise SourceAPIError(
                f"Internet Archive returned HTTP {e.response.status_code} for record '{source_id}': {e}",
                details={"source": self.source_name, "source_id": source_id, "status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise SourceAPIError(
                f"Failed retrieving record '{source_id}' from Internet Archive: {e}",
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
                    f"Internet Archive media cluster unreachable at {media_url}: {e}",
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
