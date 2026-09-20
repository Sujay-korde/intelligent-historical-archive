import logging
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai.interfaces.embedding import EmbeddingProvider
from backend.app.models.search_history import SearchHistory
from backend.app.repositories.search_repo import SearchRepository
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.search.query_normalizer import normalize_search_query
from backend.app.search.ranking.base import BaseRanker

logger = logging.getLogger(__name__)


class SearchService:
    """
    Unified search service coordinating:
    User query
    → query normalization
    → semantic embedding
    → vector retrieval
    → keyword retrieval
    → metadata filtering
    → result fusion
    → ranking
    → SearchResult

    Independent of frontend UI and exposed through versioned FastAPI endpoints.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        ranker: Optional[BaseRanker] = None,
    ):
        self.session = session
        self.embedding_provider = embedding_provider
        self.search_repo = SearchRepository(session=session, ranker=ranker)

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Executes unified search request.
        """
        start_time = time.perf_counter()

        # 1. Query Normalization
        normalized_query = normalize_search_query(request.query)
        if not normalized_query:
            return SearchResponse(
                query=request.query,
                search_type=request.search_type,
                total_results=0,
                execution_time_ms=0.0,
                results=[],
            )

        # 2. Semantic Embedding Generation
        query_vector = None
        if request.search_type in ["hybrid", "semantic"]:
            try:
                query_vector = await self.embedding_provider.embed_text(normalized_query)
            except Exception as e:
                logger.warning(f"Semantic embedding generation failed for query '{normalized_query}': {e}")
                # If semantic embedding fails, continue with keyword retrieval if in hybrid mode
                if request.search_type == "semantic":
                    raise

        # 3. Hybrid Search Execution (Vector + Keyword + Metadata Filters + Fusion + Hydration)
        response = await self.search_repo.hybrid_search(
            request=request,
            query_vector=query_vector,
            normalized_query=normalized_query,
        )

        # 4. Search Analytics Recording
        try:
            history = SearchHistory(
                query=request.query,
                filters={
                    "source": request.source,
                    "record_type": request.record_type,
                    "date_start": request.date_start,
                    "date_end": request.date_end,
                    "creator": request.creator,
                    "subject": request.subject,
                    "historical_period": request.historical_period,
                    "entity_name": request.entity_name,
                },
                search_type=request.search_type.upper(),
                result_count=response.total_results,
                execution_time_ms=response.execution_time_ms,
            )
            add_res = self.session.add(history)
            if hasattr(add_res, "__await__"):
                await add_res
            await self.session.commit()
        except Exception as e:
            logger.debug(f"Failed to record search history (non-critical): {e}")

        return response
