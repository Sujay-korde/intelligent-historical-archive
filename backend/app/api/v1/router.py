from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, recommendation, search

api_router = APIRouter()

# Mount health endpoint
api_router.include_router(health.router, tags=["Health"])

# Mount search endpoint
api_router.include_router(search.router, prefix="/search", tags=["Search"])

# Mount recommendations endpoint
api_router.include_router(recommendation.router, prefix="/recommendations", tags=["Recommendations"])
