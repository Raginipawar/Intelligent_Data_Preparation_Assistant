from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.apply_schemas import JobStatus


@dataclass
class JobRecordInternal:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    dataset_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()
