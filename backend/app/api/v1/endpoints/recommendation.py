import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_recommendation_service
from backend.app.schemas.recommendation import RecommendationResponse
from backend.app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{document_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Related Archival Documents",
    description=(
        "Retrieves related documents using composite scoring based on dense vector similarity, "
        "shared knowledge entities, and archival metadata overlap (subjects, historical period)."
    ),
)
async def get_document_recommendations(
    document_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=50, description="Max recommendations to return"),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    try:
        return await recommendation_service.get_recommendations(
            document_id=document_id, limit=limit
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as e:
        logger.exception(f"Error retrieving recommendations for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred generating recommendations: {str(e)}",
        )
