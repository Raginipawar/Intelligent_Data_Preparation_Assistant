"""
apply_schemas.py — three contracts:

1. Inbound: a *tolerant* mirror of Person 2's `Suggestion`
   (app/suggestion_schemas.py::Suggestion at the repo root). We deliberately do
   NOT import Person 2's pydantic models directly — every engine defines its
   own top-level `app` package, and importing across sibling packages that
   share a name is a collision waiting to happen the moment two engines run in
   the same process (confirmed directly while integration-testing Person 1 ->
   Person 2 in this session). `extra="allow"` + defensive `.get()` reads in
   the apply/* modules mean a minor field addition on Person 2's side degrades
   gracefully instead of hard-crashing this engine.

2. Request: `ApplyRequest` (POST /apply body) and `ExportRequest` (POST /export
   body).

3. Outbound: `ApplyResult` — the processed dataset's metadata + transformation
   log. Person 4 (algorithm recommendation) consumes this next.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Inbound: tolerant mirror of Person 2's Suggestion
# ---------------------------------------------------------------------------


class _Lenient(BaseModel):
    model_config = {"extra": "allow"}


class SuggestionIn(_Lenient):
    """Validates that an inbound suggestion roughly matches Person 2's
    contract. Deliberately permissive — see module docstring. `type` and
    `target_columns` are the only fields the apply/* modules truly require;
    everything else is read defensively via .get()-style access."""

    id: str
    type: str
    target_columns: List[str] = Field(default_factory=list)
    reasoning: str = ""
    expected_impact: str = ""
    priority_rank: int = 0
    params: Dict[str, Any] = Field(default_factory=dict)
    source: str = "rule_based"
    confidence: float = 0.7


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ApplyRequest(BaseModel):
    """Body for POST /apply.

    The raw dataset is always resolved by `dataset_id` (this engine's own
    /upload storage, falling back to Person 1's co-located storage — see
    app/dataset_client.py). The suggestion list is resolved one of two ways:

      - `suggestions` inline (list of suggestion dicts — fully decoupled,
        recommended for testing or cross-machine use), or
      - `source_job_id` (Person 2's /suggest job_id) so this engine looks it
        up from Person 2's shared local storage or live API.

    `selected_suggestion_ids` is the user's chosen subset (from Person 2's
    ranked list) to actually apply — suggestions not in this list are ignored
    entirely, not even conflict-checked.
    """

    dataset_id: str
    selected_suggestion_ids: List[str]
    suggestions: Optional[List[Dict[str, Any]]] = None
    source_job_id: Optional[str] = Field(
        default=None, description="Person 2's /suggest job_id — NOT this engine's own job_id."
    )
    feature_budget: Optional[int] = Field(
        default=None, description="Max final feature (column) count. None = no budget enforced."
    )
    target_column: Optional[str] = Field(
        default=None,
        description=(
            "The dataset's target/label column, if known (e.g. from Person 1's "
            "target_detection.suggested_target). Only affects `encoding` suggestions with "
            "method='target' — without it, target encoding always degrades to frequency "
            "encoding rather than failing."
        ),
    )


class ExportRequest(BaseModel):
    """Body for POST /export."""

    apply_job_id: str
    format: str = Field(default="auto", description='"csv" | "zip" | "auto" (match original upload format)')


# ---------------------------------------------------------------------------
# Outbound: transformation log + ApplyResult
# ---------------------------------------------------------------------------


class LogStatus(str, Enum):
    APPLIED = "applied"
    BUDGET_DROP = "budget_drop"  # not a skipped suggestion — an active post-hoc column drop
    SKIPPED_NOT_SELECTED = "skipped_not_selected"
    SKIPPED_CONFLICT = "skipped_conflict"
    SKIPPED_MISSING_COLUMN = "skipped_missing_column"
    SKIPPED_ERROR = "skipped_error"


class TransformationLogEntry(BaseModel):
    order: int
    suggestion_id: Optional[str] = None
    type: Optional[str] = None  # None for a selected_suggestion_id that matched no known suggestion
    target_columns: List[str] = Field(default_factory=list)
    action: str
    reasoning: str
    status: LogStatus


class ApplyResult(BaseModel):
    dataset_id: str
    apply_job_id: str
    source_job_id: Optional[str] = None
    status: JobStatus
    applied_suggestions: List[str] = Field(default_factory=list)
    skipped_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    transformation_log: List[TransformationLogEntry] = Field(default_factory=list)
    final_columns: List[str] = Field(default_factory=list)
    n_rows: int = 0
    n_columns: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    job_id: str
    dataset_id: Optional[str] = None
    status: JobStatus
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
