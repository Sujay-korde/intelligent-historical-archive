from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    job_type: str
    status: str
    current_step: str
    progress_pct: int
    payload: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
