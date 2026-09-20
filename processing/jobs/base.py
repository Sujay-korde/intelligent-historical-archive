from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class JobTicket(BaseModel):
    job_id: str
    document_id: str
    job_type: str
    status: str
    current_step: str
    progress_pct: int = 0
    payload: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    error_message: Optional[str] = None
    created_at: datetime


class JobManager(ABC):
    @abstractmethod
    async def enqueue(self, document_id: str, job_type: str, payload: Dict[str, Any]) -> JobTicket:
        """Enqueue a new processing job."""
        pass

    @abstractmethod
    async def acquire_job(self, worker_id: str) -> Optional[JobTicket]:
        """Atomically lease the next available job using FOR UPDATE SKIP LOCKED."""
        pass

    @abstractmethod
    async def update_progress(self, job_id: str, step: str, progress_pct: int) -> None:
        """Update job progress and heartbeat."""
        pass

    @abstractmethod
    async def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark job as completed with optional result payload."""
        pass

    @abstractmethod
    async def fail_job(
        self, job_id: str, error_message: str, error_stack: Optional[str] = None
    ) -> None:
        """Mark job as failed with error details."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[JobTicket]:
        """Retrieve job status by ID."""
        pass
