import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.document_entity import DocumentEntity
from backend.app.models.entity import Entity
from backend.app.models.relationship import Relationship
from backend.app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class EntityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_entity(
        self,
        name: str,
        entity_type: str,
        authority_uri: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Entity:
        norm_name = name.strip().lower()
        stmt = select(Entity).where(
            Entity.entity_type == entity_type,
            Entity.normalized_name == norm_name,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            if authority_uri and not existing.authority_uri:
                existing.authority_uri = authority_uri
            if description and not existing.description:
                existing.description = description
            return existing

        new_entity = Entity(
            name=name.strip(),
            normalized_name=norm_name,
            entity_type=entity_type,
            authority_uri=authority_uri,
            description=description,
        )
        self.session.add(new_entity)
        await self.session.flush()
        return new_entity

    async def link_document_entity(
        self,
        document_id: uuid.UUID,
        entity_id: uuid.UUID,
        confidence: float = 1.0,
        provenance: str = "AI",
        relationship_type: str = "MENTIONS",
    ) -> DocumentEntity:
        stmt = select(DocumentEntity).where(
            DocumentEntity.document_id == document_id,
            DocumentEntity.entity_id == entity_id,
            DocumentEntity.relationship_type == relationship_type,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        doc_ent = DocumentEntity(
            document_id=document_id,
            entity_id=entity_id,
            confidence=confidence,
            provenance=provenance,
            relationship_type=relationship_type,
        )
        self.session.add(doc_ent)
        await self.session.flush()
        return doc_ent

    async def create_relationship(
        self,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
        confidence: float = 1.0,
        source_document_id: Optional[uuid.UUID] = None,
    ) -> Relationship:
        rel = Relationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            confidence=confidence,
            source_document_id=source_document_id,
        )
        self.session.add(rel)
        await self.session.flush()
        return rel

    async def get_entities_for_document(self, document_id: uuid.UUID) -> List[Entity]:
        stmt = (
            select(Entity)
            .join(DocumentEntity, DocumentEntity.entity_id == Entity.id)
            .where(DocumentEntity.document_id == document_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_graph(self, document_id: Optional[uuid.UUID] = None, limit: int = 100) -> GraphResponse:
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes = set()

        if document_id:
            # Document-centric subgraph
            entities = await self.get_entities_for_document(document_id)
            for ent in entities:
                ent_id = str(ent.id)
                if ent_id not in seen_nodes:
                    nodes.append(
                        GraphNode(
                            id=ent_id,
                            label=ent.name,
                            group=ent.entity_type,
                            metadata={"authority_uri": ent.authority_uri},
                        )
                    )
                    seen_nodes.add(ent_id)

                # Connect document node
                doc_id_str = str(document_id)
                if doc_id_str not in seen_nodes:
                    nodes.append(
                        GraphNode(
                            id=doc_id_str,
                            label="Document",
                            group="DOCUMENT",
                        )
                    )
                    seen_nodes.add(doc_id_str)

                edges.append(
                    GraphEdge(
                        source=doc_id_str,
                        target=ent_id,
                        relationship="MENTIONS",
                        confidence=1.0,
                    )
                )

            # Query relationships between these entities
            ent_ids = [e.id for e in entities]
            if ent_ids:
                rel_stmt = (
                    select(Relationship)
                    .where(
                        Relationship.source_entity_id.in_(ent_ids),
                        Relationship.target_entity_id.in_(ent_ids),
                    )
                    .limit(limit)
                )
                rels = (await self.session.execute(rel_stmt)).scalars().all()
                for r in rels:
                    edges.append(
                        GraphEdge(
                            source=str(r.source_entity_id),
                            target=str(r.target_entity_id),
                            relationship=r.relationship_type,
                            confidence=float(r.confidence),
                        )
                    )
        else:
            # Global knowledge graph
            rel_stmt = select(Relationship).options(
                selectinload(Relationship.source_entity),
                selectinload(Relationship.target_entity),
            ).limit(limit)
            rels = (await self.session.execute(rel_stmt)).scalars().all()

            for r in rels:
                s_id = str(r.source_entity_id)
                t_id = str(r.target_entity_id)

                if s_id not in seen_nodes and r.source_entity:
                    nodes.append(
                        GraphNode(
                            id=s_id,
                            label=r.source_entity.name,
                            group=r.source_entity.entity_type,
                        )
                    )
                    seen_nodes.add(s_id)

                if t_id not in seen_nodes and r.target_entity:
                    nodes.append(
                        GraphNode(
                            id=t_id,
                            label=r.target_entity.name,
                            group=r.target_entity.entity_type,
                        )
                    )
                    seen_nodes.add(t_id)

                edges.append(
                    GraphEdge(
                        source=s_id,
                        target=t_id,
                        relationship=r.relationship_type,
                        confidence=float(r.confidence),
                    )
                )

        return GraphResponse(nodes=nodes, edges=edges)
