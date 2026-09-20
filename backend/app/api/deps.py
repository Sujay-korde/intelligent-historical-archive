from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import EmbeddingProvider, LLMProvider
from ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider
from ai.embeddings.mock_embedding_provider import MockEmbeddingProvider
from ai.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.mock_provider import MockLLMProvider
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.services.graph_service import GraphService
from backend.app.services.ingestion_service import IngestionService
from backend.app.services.processing_service import ProcessingService
from backend.app.services.search_service import SearchService
from processing.jobs.base import JobManager
from processing.jobs.postgres_job_manager import PostgresJobManager
from storage.base import StorageProvider
from storage.local_storage import LocalStorageProvider

# Global Singletons for Stateless Providers
_storage_provider: StorageProvider = LocalStorageProvider(base_dir=settings.STORAGE_LOCAL_DIR)
_job_manager: JobManager = PostgresJobManager()


def get_storage_provider() -> StorageProvider:
    return _storage_provider


def get_job_manager() -> JobManager:
    return _job_manager


def get_llm_provider() -> LLMProvider:
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY)
    return MockLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "sentence_transformers":
        return SentenceTransformerProvider(model_name=settings.EMBEDDING_MODEL)
    elif settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)
    return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)


def get_ingestion_service(
    session: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    job_mgr: JobManager = Depends(get_job_manager),
) -> IngestionService:
    return IngestionService(session=session, storage_provider=storage, job_manager=job_mgr)


def get_processing_service(
    session: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    llm: LLMProvider = Depends(get_llm_provider),
    embedding: EmbeddingProvider = Depends(get_embedding_provider),
    job_mgr: JobManager = Depends(get_job_manager),
) -> ProcessingService:
    return ProcessingService(
        session=session,
        storage_provider=storage,
        llm_provider=llm,
        embedding_provider=embedding,
        job_manager=job_mgr,
    )


def get_search_service(
    session: AsyncSession = Depends(get_db),
    embedding: EmbeddingProvider = Depends(get_embedding_provider),
) -> SearchService:
    return SearchService(session=session, embedding_provider=embedding)


def get_graph_service(
    session: AsyncSession = Depends(get_db),
) -> GraphService:
    return GraphService(session=session)
