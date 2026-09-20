import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.app.schemas.canonical import (
    CanonicalArchiveRecord,
    CreatorItem,
    MediaAsset,
    ProvenanceItem,
    SearchPage,
    SourceRawRecord,
    SourceSearchResult,
)
from ingestion.base import SourceAdapter


class LocalUploadAdapter(SourceAdapter):
    """
    Adapter for directly uploaded documents and local files.
    """

    @property
    def source_name(self) -> str:
        return "upload"

    async def search(self, query: str, limit: int = 10, cursor: Optional[str] = None) -> SearchPage:
        # Local upload does not have an external search catalog
        return SearchPage(results=[], next_cursor=None, total_count=0)

    async def fetch_record(self, source_id: str) -> SourceRawRecord:
        return SourceRawRecord(
            source=self.source_name,
            source_id=source_id,
            raw_data={"source_id": source_id},
        )

    async def stream_media(self, media_url: str) -> AsyncIterator[bytes]:
        raise NotImplementedError("Direct uploads provide file bytes directly.")

    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        data = raw_record.raw_data
        title = data.get("title", "Uploaded Document")
        creator = data.get("creator")
        creators = [CreatorItem(name=creator, role="author")] if creator else []
        date_raw = data.get("date")

        media_assets = []
        if data.get("file_path"):
            mime_type = data.get("mime_type", "application/pdf")
            media_type = "document" if "pdf" in mime_type or "text" in mime_type else "image"
            media_assets.append(
                MediaAsset(
                    asset_id=f"upload_{uuid.uuid4().hex[:8]}",
                    asset_role="primary",
                    media_type=media_type,
                    mime_type=mime_type,
                    storage_key=data.get("file_path"),
                )
            )

        provenance = [
            ProvenanceItem(field="title", value=title, source="USER", confidence=1.0),
        ]

        return CanonicalArchiveRecord(
            source=self.source_name,
            source_id=raw_record.source_id,
            title=title,
            description=data.get("description"),
            creators=creators,
            date_raw=date_raw,
            language=data.get("language", "English"),
            record_type=data.get("record_type", "document"),
            media_assets=media_assets,
            subjects=data.get("subjects", []),
            raw_metadata=data,
            provenance_records=provenance,
        )
