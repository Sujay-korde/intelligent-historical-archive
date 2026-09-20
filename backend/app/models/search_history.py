import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    query = Column(Text, nullable=False)
    filters = Column(JSONB, nullable=False, default=dict)
    search_type = Column(String(32), nullable=False, default="HYBRID")  # HYBRID, SEMANTIC, KEYWORD
    result_count = Column(Integer, nullable=False, default=0)
    execution_time_ms = Column(Numeric(8, 2), nullable=True)
    selected_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    selected_document = relationship("Document")
