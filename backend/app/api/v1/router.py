from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    documents,
    graph,
    health,
    ingest,
    media,
    recommendation,
    search,
    stats,
)

api_router = APIRouter()

# Mount health endpoint
api_router.include_router(health.router, tags=["Health"])

# Mount search endpoint
api_router.include_router(search.router, prefix="/search", tags=["Search"])

# Mount recommendations endpoint
api_router.include_router(recommendation.router, prefix="/recommendations", tags=["Recommendations"])

# Mount documents endpoint
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Mount ingestion & deposit endpoint
api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingestion & Deposit"])

# Mount knowledge graph endpoint
api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])

# Mount media asset streaming endpoint
api_router.include_router(media.router, prefix="/media", tags=["Media"])

# Mount repository statistics endpoint
api_router.include_router(stats.router, prefix="/stats", tags=["Statistics"])
