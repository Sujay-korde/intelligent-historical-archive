import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(64), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    record_type = Column(String(64), nullable=False, default="document")
    source_url = Column(String(2048), nullable=True)
    status = Column(String(32), nullable=False, default="INGESTED", index=True)
    processing_stage = Column(String(64), nullable=False, default="INITIAL", index=True)
    quality_score = Column(Numeric(5, 2), default=0.0)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_documents_source_source_id"),
    )

    # Relationships
    media_assets = relationship("DocumentMediaAsset", back_populates="document", cascade="all, delete-orphan")
    doc_metadata = relationship("DocumentMetadata", back_populates="document", uselist=False, cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("DocumentEntity", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")
