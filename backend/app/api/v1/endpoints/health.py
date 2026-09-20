from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from storage.base import StorageProvider
from backend.app.api.deps import get_storage_provider

router = APIRouter()


class DatabaseHealth(BaseModel):
    connected: bool
    pgvector_installed: bool
    details: Optional[str] = None


class StorageHealth(BaseModel):
    backend: str
    operational: bool
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    project_name: str
    environment: str
    version: str
    database: DatabaseHealth
    storage: StorageHealth


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def get_health(
    session: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> HealthResponse:
    """Comprehensive health check checking DB connectivity, pgvector extension, and storage."""
    db_connected = False
    pgvector_installed = False
    db_details = "Operational"

    try:
        # Check database connectivity
        result = await session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_connected = True

        # Check pgvector extension
        ext_result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        if ext_result.scalar_one_or_none():
            pgvector_installed = True
        else:
            pgvector_installed = False
            db_details = "Connected, but pgvector extension is not yet loaded in active DB"
    except Exception as e:
        db_connected = False
        pgvector_installed = False
        db_details = f"Database connection error: {str(e)}"
        logger.warning(f"Health check DB probe notice: {e}")

    # Check storage health
    storage_operational = True
    storage_details = "Operational"
    try:
        if not storage:
            storage_operational = False
            storage_details = "Storage provider uninitialized"
    except Exception as e:
        storage_operational = False
        storage_details = str(e)

    overall_status = "healthy" if db_connected and pgvector_installed and storage_operational else "degraded"

    return HealthResponse(
        status=overall_status,
        project_name=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        database=DatabaseHealth(
            connected=db_connected,
            pgvector_installed=pgvector_installed,
            details=db_details,
        ),
        storage=StorageHealth(
            backend=settings.STORAGE_BACKEND,
            operational=storage_operational,
            details=storage_details,
        ),
    )


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """Lightweight readiness/liveness ping endpoint."""
    return {"status": "ok", "message": "pong"}
