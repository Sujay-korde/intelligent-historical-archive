import time
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import EmbeddingProvider
from backend.app.models.search_history import SearchHistory
from backend.app.repositories.search_repo import SearchRepository
from backend.app.schemas.search import SearchRequest, SearchResponse


class SearchService:
    def __init__(self, session: AsyncSession, embedding_provider: EmbeddingProvider):
        self.session = session
        self.embedding_provider = embedding_provider
        self.search_repo = SearchRepository(session)

    async def search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.perf_counter()

        # Generate query vector for semantic search if applicable
        query_vector = None
        if request.search_type in ["hybrid", "semantic"]:
            query_vector = await self.embedding_provider.embed_text(request.query)

        response = await self.search_repo.hybrid_search(request, query_vector=query_vector)

        # Record in SearchHistory for analytics
        try:
            history = SearchHistory(
                query=request.query,
                filters={
                    "source": request.source,
                    "record_type": request.record_type,
                    "date_start": request.date_start,
                    "date_end": request.date_end,
                },
                search_type=request.search_type.upper(),
                result_count=response.total_results,
                execution_time_ms=response.execution_time_ms,
            )
            self.session.add(history)
            await self.session.commit()
        except Exception:
            pass

        return response
