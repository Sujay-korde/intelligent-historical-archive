import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.config import settings
from backend.app.core.database import Base


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=False)
    dimension = Column(Integer, nullable=False, default=settings.EMBEDDING_DIMENSION)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("chunk_id", "model_name", "model_version", name="uq_chunk_embedding_model"),
    )

    chunk = relationship("DocumentChunk", back_populates="embeddings")
