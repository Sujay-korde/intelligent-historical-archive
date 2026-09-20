from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    logger.info(f"Database URL configured: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"Storage Backend configured: {settings.STORAGE_BACKEND}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_application() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Scalable Multi-Format Document Ingestion, Processing, and RAG/Vector Retrieval Platform",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "path": request.url.path},
        )

    # Root informational route
    @app.get("/", tags=["General"])
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "docs_url": f"{settings.API_V1_STR}/docs",
            "health_url": f"{settings.API_V1_STR}/health",
        }

    # Mount /health at top-level as well as within API v1
    app.include_router(health_router, prefix="", tags=["Health"])
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
