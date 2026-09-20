import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    current_step = Column(String(128), nullable=False, default="QUEUED")
    progress_pct = Column(Integer, nullable=False, default=0)
    payload = Column(JSONB, nullable=False, default=dict)
    result = Column(JSONB, nullable=False, default=dict)
    locked_by = Column(String(128), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    document = relationship("Document", back_populates="jobs")
