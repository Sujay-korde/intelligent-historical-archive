import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    creators = Column(JSONB, nullable=False, default=list)  # list of {name, role, authority_id}
    date_raw = Column(String(128), nullable=True)
    date_start = Column(Date, nullable=True, index=True)
    date_end = Column(Date, nullable=True, index=True)
    date_is_circa = Column(Boolean, default=False)
    locations = Column(JSONB, nullable=False, default=list)
    language = Column(String(64), default="English")
    organization = Column(Text, nullable=True)
    subjects = Column(JSONB, nullable=False, default=list)
    rights = Column(JSONB, nullable=False, default=dict)
    external_ids = Column(JSONB, nullable=False, default=dict)
    raw_metadata = Column(JSONB, nullable=False, default=dict)
    ai_metadata = Column(JSONB, nullable=False, default=dict)
    provenance = Column(JSONB, nullable=False, default=list)
    confidence = Column(Numeric(4, 3), default=1.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="doc_metadata")
