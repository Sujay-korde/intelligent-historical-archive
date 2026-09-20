import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_document_repository
from backend.app.repositories.document_repo import DocumentRepository
from backend.app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentMediaAssetResponse,
    DocumentMetadataResponse,
    DocumentSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_doc_summary(doc) -> DocumentSummaryResponse:
    return DocumentSummaryResponse(
        id=doc.id,
        source=doc.source,
        source_id=doc.source_id,
        title=doc.title,
        description=doc.description,
        record_type=doc.record_type,
        source_url=doc.source_url,
        status=doc.status,
        processing_stage=doc.processing_stage,
        quality_score=float(doc.quality_score or 0.0),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Archival Documents",
    description="Retrieve paginated list of ingested historical archive documents.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. READY, INGESTED)"),
    doc_repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentListResponse:
    try:
        docs, total = await doc_repo.list_documents(
            page=page, page_size=page_size, source=source, status=status
        )
        return DocumentListResponse(
            items=[_format_doc_summary(d) for d in docs],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.exception(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Detail & Provenance",
    description="Retrieve full document record with physical assets, metadata provenance, and extracted knowledge entities.",
)
async def get_document(
    document_id: uuid.UUID,
    doc_repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentDetailResponse:
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found in archive.",
        )

    meta_resp = None
    if doc.doc_metadata:
        m = doc.doc_metadata
        creators_list = []
        if m.creators:
            for c in m.creators:
                if isinstance(c, dict):
                    creators_list.append(c)
                elif isinstance(c, str):
                    creators_list.append({"name": c, "role": "Author"})
                else:
                    creators_list.append({"name": str(c), "role": "Author"})

        prov_list = []
        if m.provenance:
            if isinstance(m.provenance, list):
                prov_list = m.provenance
            elif isinstance(m.provenance, dict):
                prov_list = [m.provenance]

        meta_resp = DocumentMetadataResponse(
            creators=creators_list,
            date_raw=m.date_raw,
            date_start=m.date_start.isoformat() if m.date_start else None,
            date_end=m.date_end.isoformat() if m.date_end else None,
            date_is_circa=bool(m.date_is_circa),
            locations=m.locations or [],
            language=m.language or "English",
            organization=m.organization,
            subjects=m.subjects or [],
            rights=m.rights or {},
            external_ids=m.external_ids or {},
            raw_metadata=m.raw_metadata or {},
            ai_metadata=m.ai_metadata or {},
            provenance=prov_list,
            confidence=float(m.confidence or 1.0),
        )

    assets_resp = []
    for asset in (doc.media_assets or []):
        assets_resp.append(
            DocumentMediaAssetResponse(
                id=asset.id,
                asset_role=asset.asset_role,
                media_type=asset.media_type,
                mime_type=asset.mime_type,
                storage_key=asset.storage_key,
                access_url=f"/api/v1/media/{asset.storage_key}",
                file_size_bytes=asset.file_size_bytes,
                page_number=asset.page_number,
            )
        )

    summary = _format_doc_summary(doc)
    return DocumentDetailResponse(
        **summary.model_dump(),
        metadata=meta_resp,
        media_assets=assets_resp,
        entities_count=len(doc.entities or []),
        chunks_count=len(doc.chunks or []),
    )
