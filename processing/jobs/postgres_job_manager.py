import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import async_session_factory
from backend.app.models.job import ProcessingJob
from processing.jobs.base import JobManager, JobTicket


class PostgresJobManager(JobManager):
    """
    PostgreSQL-backed Job Queue using FOR UPDATE SKIP LOCKED row leasing.
    Crash-resilient, multi-worker ready, and requires zero external queue infrastructure.
    """

    def _to_ticket(self, job: ProcessingJob) -> JobTicket:
        return JobTicket(
            job_id=str(job.id),
            document_id=str(job.document_id),
            job_type=job.job_type,
            status=job.status,
            current_step=job.current_step,
            progress_pct=job.progress_pct,
            payload=job.payload or {},
            result=job.result or {},
            error_message=job.error_message,
            created_at=job.created_at,
        )

    async def enqueue(self, document_id: str, job_type: str, payload: Dict[str, Any]) -> JobTicket:
        async with async_session_factory() as session:
            job = ProcessingJob(
                document_id=uuid.UUID(document_id),
                job_type=job_type,
                status="PENDING",
                current_step="QUEUED",
                progress_pct=0,
                payload=payload,
                max_retries=settings.MAX_JOB_RETRIES,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return self._to_ticket(job)

    async def acquire_job(self, worker_id: str) -> Optional[JobTicket]:
        lease_timeout = datetime.utcnow() - timedelta(seconds=settings.JOB_LEASE_SECONDS)
        async with async_session_factory() as session:
            # Query for next available job with SKIP LOCKED
            stmt = (
                select(ProcessingJob)
                .where(
                    or_(
                        ProcessingJob.status == "PENDING",
                        and_(
                            ProcessingJob.status == "RUNNING",
                            ProcessingJob.heartbeat_at < lease_timeout,
                        ),
                    )
                )
                .order_by(ProcessingJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                return None

            job.status = "RUNNING"
            job.locked_by = worker_id
            job.locked_at = datetime.utcnow()
            job.heartbeat_at = datetime.utcnow()
            job.started_at = job.started_at or datetime.utcnow()

            await session.commit()
            await session.refresh(job)
            return self._to_ticket(job)

    async def update_progress(self, job_id: str, step: str, progress_pct: int) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(ProcessingJob)
                .where(ProcessingJob.id == uuid.UUID(job_id))
                .values(
                    current_step=step,
                    progress_pct=progress_pct,
                    heartbeat_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(ProcessingJob)
                .where(ProcessingJob.id == uuid.UUID(job_id))
                .values(
                    status="COMPLETED",
                    progress_pct=100,
                    current_step="COMPLETED",
                    result=result or {},
                    completed_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def fail_job(
        self, job_id: str, error_message: str, error_stack: Optional[str] = None
    ) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(ProcessingJob)
                .where(ProcessingJob.id == uuid.UUID(job_id))
                .values(
                    status="FAILED",
                    error_message=error_message,
                    error_stack=error_stack,
                    completed_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def get_job(self, job_id: str) -> Optional[JobTicket]:
        async with async_session_factory() as session:
            stmt = select(ProcessingJob).where(ProcessingJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            return self._to_ticket(job) if job else None
