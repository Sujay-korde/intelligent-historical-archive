from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str
    entity_type: str
    authority_uri: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    documents_count: int = 0


class EntityDetailResponse(EntityResponse):
    related_documents: List[Dict[str, Any]] = []
    connected_entities: List[Dict[str, Any]] = []
