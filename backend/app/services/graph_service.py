import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.entity_repo import EntityRepository
from backend.app.schemas.graph import GraphResponse


class GraphService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.entity_repo = EntityRepository(session)

    async def get_graph(
        self, document_id: Optional[uuid.UUID] = None, limit: int = 100
    ) -> GraphResponse:
        return await self.entity_repo.get_graph(document_id=document_id, limit=limit)
