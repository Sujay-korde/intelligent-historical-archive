import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)  # PERSON, ORGANIZATION, LOCATION, EVENT, DATE, TOPIC
    authority_uri = Column(String(512), nullable=True)  # Wikidata, VIAF, LOC URI
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "normalized_name", name="uq_entities_type_name"),
    )

    documents = relationship("DocumentEntity", back_populates="entity", cascade="all, delete-orphan")
