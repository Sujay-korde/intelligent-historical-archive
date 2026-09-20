from sqlalchemy import Column, ForeignKey, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Numeric(4, 3), nullable=False, default=1.0)
    provenance = Column(String(32), nullable=False, default="SOURCE")  # SOURCE, AI, USER, FILE
    relationship_type = Column(String(64), nullable=False, default="MENTIONS")

    __table_args__ = (
        PrimaryKeyConstraint("document_id", "entity_id", "relationship_type"),
    )

    document = relationship("Document", back_populates="entities")
    entity = relationship("Entity", back_populates="documents")
