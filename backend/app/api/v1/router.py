from fastapi import APIRouter
from backend.app.api.v1.endpoints import health

api_router = APIRouter()

# Mount health endpoint
api_router.include_router(health.router, tags=["Health"])
