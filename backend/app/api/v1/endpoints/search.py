import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_search_service
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Archival Search",
    description=(
        "Executes a unified search combining dense semantic vector retrieval (pgvector), "
        "PostgreSQL keyword/full-text retrieval, and archival metadata filtering. "
        "Fuses signals using modular Reciprocal Rank Fusion (RRF) and returns rich document metadata, "
        "contextual snippets, and media preview information."
    ),
)
async def search_documents_post(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    try:
        return await search_service.search(request)
    except Exception as e:
        logger.exception(f"Search request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred executing the search: {str(e)}",
        )


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Archival Search (URL Query Parameters)",
    description="Convenience GET endpoint allowing query parameter based archival searches.",
)
async def search_documents_get(
    q: str = Query(..., min_length=1, description="Search query string"),
    search_type: str = Query("hybrid", description="Search mode: hybrid, semantic, keyword"),
    limit: int = Query(10, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., loc, internet_archive)"),
    record_type: Optional[str] = Query(None, description="Filter by record type (e.g., document, audio, manuscript)"),
    date_start: Optional[str] = Query(None, description="Filter start date"),
    date_end: Optional[str] = Query(None, description="Filter end date"),
    creator: Optional[str] = Query(None, description="Filter by creator name"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    historical_period: Optional[str] = Query(None, description="Filter by historical period"),
    entity_name: Optional[str] = Query(None, description="Filter by entity name"),
    semantic_weight: float = Query(0.7, ge=0.0, le=1.0, description="Semantic vector weight"),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0, description="Keyword text weight"),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    request = SearchRequest(
        query=q,
        search_type=search_type,
        limit=limit,
        offset=offset,
        source=source,
        record_type=record_type,
        date_start=date_start,
        date_end=date_end,
        creator=creator,
        subject=subject,
        historical_period=historical_period,
        entity_name=entity_name,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
    )
    try:
        return await search_service.search(request)
    except Exception as e:
        logger.exception(f"GET search request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred executing the search: {str(e)}",
        )
