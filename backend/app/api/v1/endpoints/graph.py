import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_graph_service
from backend.app.schemas.graph import GraphResponse
from backend.app.services.graph_service import GraphService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Graph Network",
    description="Retrieve nodes and relationship edges across entities and documents for network visualization.",
)
async def get_knowledge_graph(
    document_id: Optional[uuid.UUID] = Query(None, description="Optional document UUID to filter local subgraph"),
    limit: int = Query(150, ge=1, le=500, description="Max relationships to return"),
    graph_service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    try:
        return await graph_service.get_graph(document_id=document_id, limit=limit)
    except Exception as e:
        logger.exception(f"Error generating knowledge graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate knowledge graph: {str(e)}",
        )
