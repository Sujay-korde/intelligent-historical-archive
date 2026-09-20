import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class DocumentMediaAsset(Base):
    __tablename__ = "document_media_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_role = Column(String(32), nullable=False, default="primary")  # primary, thumbnail, scan_page, transcript
    media_type = Column(String(32), nullable=False)  # document, image, audio, video
    mime_type = Column(String(128), nullable=False)
    storage_key = Column(String(1024), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True, index=True)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="media_assets")
