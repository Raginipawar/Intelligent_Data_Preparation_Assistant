"""
recommend_job_queue.py — shared background job queue for person4_engine.
Matches the exact get_job_queue() interface used across Persons 1-3.
"""
from __future__ import annotations

import json
import traceback
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from app import recommend_config as config
from app.jobs.recommend_job_record import JobRecordInternal
from app.recommend_schemas import JobStatus


def _job_path(job_id: str):
    return config.JOBS_DIR / f"{job_id}.json"


def _persist(record: JobRecordInternal) -> None:
    try:
        payload = {
            "job_id": record.job_id,
            "status": record.status.value,
            "dataset_id": record.dataset_id,
            "error": record.error,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "has_result": record.result is not None,
        }
        _job_path(record.job_id).write_text(json.dumps(payload, indent=2))
    except OSError:
        pass


class JobQueue(ABC):
    @abstractmethod
    def new_job(self, dataset_id: Optional[str] = None) -> str:
        ...

    @abstractmethod
    def submit(self, job_id: str, func: Callable, *args: Any, **kwargs: Any) -> None:
        ...

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[JobRecordInternal]:
        ...


class InMemoryJobQueue(JobQueue):
    def __init__(self, max_workers: int = config.THREAD_POOL_WORKERS):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, JobRecordInternal] = {}

    def new_job(self, dataset_id: Optional[str] = None) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecordInternal(job_id=job_id, status=JobStatus.PENDING, dataset_id=dataset_id)
        self._jobs[job_id] = record
        _persist(record)
        return job_id

    def submit(self, job_id: str, func: Callable, *args: Any, **kwargs: Any) -> None:
        record = self._jobs.get(job_id)
        if record is None:
            raise KeyError(f"Unknown job_id {job_id!r} — call new_job() first")

        def _run():
            record.status = JobStatus.RUNNING
            record.touch()
            _persist(record)
            try:
                result = func(*args, **kwargs)
                record.result = result
                record.status = JobStatus.SUCCESS
            except Exception as exc:
                record.error = f"{exc}\n{traceback.format_exc()}"
                record.status = JobStatus.FAILED
            record.touch()
            _persist(record)

        self._executor.submit(_run)

    def get_job(self, job_id: str) -> Optional[JobRecordInternal]:
        return self._jobs.get(job_id)


_queue_singleton: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    global _queue_singleton
    if _queue_singleton is None:
        _queue_singleton = InMemoryJobQueue()
    return _queue_singleton
