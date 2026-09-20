import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(64), nullable=False, index=True)  # AUTHORED, LOCATED_IN, AFFILIATED_WITH, PART_OF, RELATED_TO
    confidence = Column(Numeric(4, 3), nullable=False, default=1.0)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    source_entity = relationship("Entity", foreign_keys=[source_entity_id])
    target_entity = relationship("Entity", foreign_keys=[target_entity_id])
    source_document = relationship("Document")
