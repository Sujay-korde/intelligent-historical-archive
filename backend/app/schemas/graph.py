from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    group: str  # entity_type or 'document'
    metadata: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    confidence: float = 1.0


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
