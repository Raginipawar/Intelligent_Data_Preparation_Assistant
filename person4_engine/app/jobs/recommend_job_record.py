"""
recommend_job_record.py — Internal record structure for job tracking.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from app.recommend_schemas import JobStatus


@dataclass
class JobRecordInternal:
    job_id: str
    status: JobStatus
    dataset_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()
