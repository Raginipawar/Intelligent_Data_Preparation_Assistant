"""
queue.py — the shared background job-queue pattern.

Every person's endpoint (Person 1's /analyze, Person 2's /suggest, Person 3's
/apply + /export, Person 4's /recommend) should go through THIS abstraction
instead of rolling its own threading/async logic. That's what makes the four
modules composable into one pipeline instead of four different concurrency
models glued together.

Usage from any module:

    from app.jobs.queue import get_job_queue

    queue = get_job_queue()
    job_id = queue.new_job(dataset_id="abc123")
    queue.submit(job_id, my_heavy_function, arg1, arg2)
    ...
    record = queue.get_job(job_id)   # -> JobRecordInternal (status/result/error)

Swapping backends (e.g. once the team wants real distributed workers) is a
config change (app.config.JOB_QUEUE_BACKEND = "celery"), not a rewrite of
every endpoint — as long as new endpoints keep using this interface.
"""
from __future__ import annotations

import json
import traceback
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from app import config
from app.jobs.models import JobRecordInternal
from app.schemas import JobStatus


def _job_path(job_id: str):
    return config.JOBS_DIR / f"{job_id}.json"


def _persist(record: JobRecordInternal) -> None:
    """Best-effort disk persistence so job status survives a process restart
    and can be inspected outside the running server if needed."""
    try:
        payload = {
            "job_id": record.job_id,
            "status": record.status.value,
            "dataset_id": record.dataset_id,
            "error": record.error,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            # Full result JSON is written separately by the caller (can be large);
            # here we just persist status/metadata so polling doesn't need the blob.
            "has_result": record.result is not None,
        }
        _job_path(record.job_id).write_text(json.dumps(payload, indent=2))
    except OSError:
        pass  # persistence is a convenience, never fatal to the request


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
    """Default backend. Zero external dependencies — runs jobs on a thread
    pool inside the same process. Good enough for local dev and for a
    single-machine demo; swap to CeleryJobQueue when you need real workers."""

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
            except Exception as exc:  # noqa: BLE001 — surface any failure to the caller
                record.error = f"{exc}\n{traceback.format_exc()}"
                record.status = JobStatus.FAILED
            record.touch()
            _persist(record)

        self._executor.submit(_run)

    def get_job(self, job_id: str) -> Optional[JobRecordInternal]:
        return self._jobs.get(job_id)


class CeleryJobQueue(JobQueue):
    """Skeleton for a real distributed backend. Not wired up by default —
    activate by setting JOB_QUEUE_BACKEND=celery and installing celery+redis.

    Each person's heavy function still gets registered as a Celery task; the
    new_job/submit/get_job interface stays identical so endpoint code never
    has to know which backend is active.
    """

    def __init__(self):
        try:
            from celery import Celery  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "JOB_QUEUE_BACKEND=celery requires `pip install celery redis` "
                "and a running Redis instance. Falling back to the in-memory "
                "queue is safer for local dev — unset JOB_QUEUE_BACKEND to do that."
            ) from exc

        from celery import Celery

        self._app = Celery(
            "person1_engine",
            broker=config.CELERY_BROKER_URL,
            backend=config.CELERY_RESULT_BACKEND,
        )
        self._results: Dict[str, Any] = {}

        @self._app.task(name="run_job")
        def run_job(func_path: str, args: list, kwargs: dict):  # pragma: no cover
            import importlib

            module_path, func_name = func_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            return func(*args, **kwargs)

        self._run_job_task = run_job
        self._jobs: Dict[str, JobRecordInternal] = {}

    def new_job(self, dataset_id: Optional[str] = None) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobRecordInternal(job_id=job_id, status=JobStatus.PENDING, dataset_id=dataset_id)
        return job_id

    def submit(self, job_id: str, func: Callable, *args: Any, **kwargs: Any) -> None:
        record = self._jobs[job_id]
        func_path = f"{func.__module__}.{func.__qualname__}"
        async_result = self._run_job_task.delay(func_path, list(args), kwargs)
        self._results[job_id] = async_result
        record.status = JobStatus.RUNNING
        record.touch()

    def get_job(self, job_id: str) -> Optional[JobRecordInternal]:
        record = self._jobs.get(job_id)
        if record is None:
            return None
        async_result = self._results.get(job_id)
        if async_result is not None:
            if async_result.successful():
                record.status = JobStatus.SUCCESS
                record.result = async_result.result
            elif async_result.failed():
                record.status = JobStatus.FAILED
                record.error = str(async_result.result)
        return record


_queue_singleton: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Every module (Person 1-4) should call this instead of instantiating
    a queue directly, so the whole app shares one backend/instance."""
    global _queue_singleton
    if _queue_singleton is None:
        if config.JOB_QUEUE_BACKEND == "celery":
            _queue_singleton = CeleryJobQueue()
        else:
            _queue_singleton = InMemoryJobQueue()
    return _queue_singleton
