"""
recommend_schemas.py — Pydantic models for Person 4 (Algorithm Recommendation Engine).
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


class TaskType(str, Enum):
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    REGRESSION = "regression"
    UNKNOWN = "unknown"


class MetaFeatures(BaseModel):
    n_rows: int = 0
    n_columns: int = 0
    n_features: int = 0
    feature_to_sample_ratio: float = 0.0
    task_type: TaskType = TaskType.UNKNOWN
    target_column: Optional[str] = None
    target_cardinality: int = 0
    n_numerical: int = 0
    n_categorical: int = 0
    n_boolean: int = 0
    n_text: int = 0
    n_datetime: int = 0
    class_imbalance_ratio: float = 1.0
    missing_cell_pct: float = 0.0
    high_skew_count: int = 0
    mean_absolute_correlation: float = 0.0


class BenchmarkResult(BaseModel):
    metric: str
    score: float
    cv_scores: List[float] = Field(default_factory=list)
    fit_time_seconds: float = 0.0
    status: str = "completed"
    note: Optional[str] = None


class AlgorithmRecommendation(BaseModel):
    algorithm: str
    model_class: str
    rank: int
    recommendation_score: float
    reasoning: List[str] = Field(default_factory=list)
    benchmark: Optional[BenchmarkResult] = None
    suitability: str = "high"  # "high" | "medium" | "low"


class RecommendationReport(BaseModel):
    status: JobStatus = JobStatus.SUCCESS
    job_id: str
    dataset_id: str
    apply_job_id: Optional[str] = None
    task_type: TaskType
    target_column: Optional[str] = None
    dataset_meta_features: MetaFeatures
    recommendations: List[AlgorithmRecommendation] = Field(default_factory=list)
    benchmarked: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)


class RecommendRequest(BaseModel):
    dataset_id: str
    apply_job_id: Optional[str] = Field(
        default=None,
        description="Person 3's POST /apply job_id. If provided, used to resolve processed dataset."
    )
    target_column: Optional[str] = Field(
        default=None,
        description="Target/label column name. If omitted, will be inferred from dataset or Person 1 report."
    )
    perform_benchmark: bool = Field(
        default=True,
        description="Whether to run empirical 5-fold CV benchmark on top recommendations."
    )
    top_k_benchmark: int = Field(
        default=3,
        description="Number of top candidate algorithms to benchmark."
    )
    custom_meta_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional pre-calculated meta-features to override extraction."
    )


class JobRecord(BaseModel):
    job_id: str
    dataset_id: Optional[str] = None
    status: JobStatus
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
