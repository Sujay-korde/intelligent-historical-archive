import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.document import Document
from backend.app.models.media_asset import DocumentMediaAsset
from backend.app.models.metadata import DocumentMetadata
from backend.app.schemas.canonical import CanonicalArchiveRecord


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_from_canonical(
        self, record: CanonicalArchiveRecord
    ) -> Document:
        # Check if record already exists
        stmt = select(Document).where(
            Document.source == record.source,
            Document.source_id == record.source_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        doc = Document(
            source=record.source,
            source_id=record.source_id,
            title=record.title,
            description=record.description,
            record_type=record.record_type,
            source_url=record.source_url,
            status="INGESTED",
            processing_stage="INITIAL",
        )
        self.session.add(doc)
        await self.session.flush()

        # Parse dates into datetime.date if string format
        d_start = None
        d_end = None
        if record.date_start:
            try:
                from datetime import datetime as dt_cls
                d_start = dt_cls.fromisoformat(record.date_start.split("T")[0]).date()
            except Exception:
                d_start = None
        if record.date_end:
            try:
                from datetime import datetime as dt_cls
                d_end = dt_cls.fromisoformat(record.date_end.split("T")[0]).date()
            except Exception:
                d_end = None

        # Add metadata
        meta = DocumentMetadata(
            document_id=doc.id,
            creators=[c.model_dump(mode="json") for c in record.creators],
            date_raw=record.date_raw,
            date_start=d_start,
            date_end=d_end,
            date_is_circa=record.date_is_circa,
            locations=record.locations,
            language=record.language or "English",
            subjects=record.subjects,
            rights=record.rights if isinstance(record.rights, dict) else {"statement": str(record.rights)},
            external_ids=record.external_ids,
            raw_metadata=record.raw_metadata,
            provenance=[p.model_dump(mode="json") for p in record.provenance_records],
        )
        self.session.add(meta)

        # Add media assets
        for asset in record.media_assets:
            m = DocumentMediaAsset(
                document_id=doc.id,
                asset_role=asset.asset_role,
                media_type=asset.media_type,
                mime_type=asset.mime_type,
                storage_key=asset.storage_key or asset.url or "",
                file_size_bytes=asset.file_size_bytes,
                checksum_sha256=asset.checksum_sha256,
                page_number=asset.page_number,
            )
            self.session.add(m)

        await self.session.flush()
        return doc

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.media_assets),
                selectinload(Document.doc_metadata),
                selectinload(Document.entities),
                selectinload(Document.chunks),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        source: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Document], int]:
        query = select(Document)
        if source:
            query = query.where(Document.source == source)
        if status:
            query = query.where(Document.status == status)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        items_stmt = (
            query.order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(selectinload(Document.doc_metadata))
        )
        items = (await self.session.execute(items_stmt)).scalars().all()
        return list(items), total

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        processing_stage: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> None:
        doc = await self.get_by_id(document_id)
        if doc:
            doc.status = status
            if processing_stage:
                doc.processing_stage = processing_stage
            if quality_score is not None:
                doc.quality_score = quality_score
            await self.session.flush()
