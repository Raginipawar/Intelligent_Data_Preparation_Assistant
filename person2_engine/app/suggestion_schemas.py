"""
schemas.py — two contracts:

1. Inbound: a *tolerant* mirror of Person 1's `DatasetHealthReport`
   (person1_engine/app/schemas.py). We deliberately do NOT import Person 1's
   pydantic models directly — both engines define their own top-level `app`
   package, and importing across sibling packages that share a name is a
   collision waiting to happen once both run in the same process/tests. This
   model is intentionally loose (`extra="allow"`, most fields optional) so a
   minor field addition on Person 1's side doesn't hard-crash /suggest; the
   rule engine in app/suggestions/*.py also reads defensively via .get().

2. Outbound: the ranked "Suggestion List" contract this engine's /suggest
   endpoint returns. Person 3 (apply/execute layer) consumes this directly —
   see README.md's "Contract notes for Person 3" section before changing
   field names here.
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
# Inbound: tolerant mirror of Person 1's Dataset Health Report
# ---------------------------------------------------------------------------


class _Lenient(BaseModel):
    model_config = {"extra": "allow"}


class HealthReportIn(_Lenient):
    """Validates that an inbound payload roughly matches Person 1's contract.
    Deliberately permissive — see module docstring."""

    dataset_id: Optional[str] = None
    job_id: Optional[str] = None
    status: Optional[str] = None
    ingestion: Optional[Dict[str, Any]] = None
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    missingness: Optional[Dict[str, Any]] = None
    distributions: Optional[Dict[str, Any]] = None
    cardinality: Optional[Dict[str, Any]] = None
    correlation: Optional[Dict[str, Any]] = None
    target_detection: Optional[Dict[str, Any]] = None
    duplicates: Optional[Dict[str, Any]] = None
    outliers: Optional[Dict[str, Any]] = None
    feature_importance_signal: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow", "populate_by_name": True}


# ---------------------------------------------------------------------------
# Outbound: the ranked Suggestion List
# ---------------------------------------------------------------------------


class SuggestionType(str, Enum):
    IMPUTATION = "imputation"
    ENCODING = "encoding"
    SCALING = "scaling"
    TRANSFORM = "transform"
    DROP_REDUNDANT = "drop_redundant"
    BINNING = "binning"
    INTERACTION = "interaction"


class Suggestion(BaseModel):
    id: str
    type: SuggestionType
    target_columns: List[str]
    reasoning: str
    expected_impact: str
    priority_rank: int = 0
    # Additive beyond the spec's minimal contract — Person 3 (apply layer) needs concrete
    # parameters to actually execute a suggestion, not just its category. See README.
    params: Dict[str, Any] = Field(default_factory=dict)
    source: str = "rule_based"  # "rule_based" | "rule_based+autogluon"
    confidence: float = 0.7


class ReportMeta(BaseModel):
    generated_at: str
    engine_version: str = "1.0.0"
    processing_time_seconds: float


class SuggestionList(BaseModel):
    dataset_id: str
    source_job_id: Optional[str] = None
    job_id: str
    status: JobStatus
    suggestions: List[Suggestion]
    automl_enrichment: Dict[str, Any] = Field(default_factory=dict)
    meta: ReportMeta


class JobRecord(BaseModel):
    job_id: str
    dataset_id: Optional[str] = None
    status: JobStatus
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class SuggestRequest(BaseModel):
    """Body for POST /suggest.

    Exactly one way to supply the health report:
      - `health_report` inline (fully decoupled — recommended for cross-machine use,
        testing, or if the caller already has Person 1's /result response in hand), or
      - `dataset_id` (+ optional `source_job_id`) so this engine looks the report up
        from Person 1's shared local storage or live API (see app/suggestion_config.py).

    `dataset_id` is always required (for bookkeeping/output labeling), even when
    `health_report` is supplied inline.
    """

    dataset_id: str
    source_job_id: Optional[str] = Field(
        default=None, description="Person 1's /analyze job_id — NOT this engine's own job_id."
    )
    health_report: Optional[Dict[str, Any]] = None
