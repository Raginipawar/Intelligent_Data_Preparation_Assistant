"""
schemas.py — The Dataset Health Report contract.

This is THE integration contract for the whole team. Person 2's /suggest endpoint
consumes exactly this JSON shape. Don't rename fields here without telling
Persons 2-4 — they'll be deserializing straight into this.
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


class SourceType(str, Enum):
    SINGLE_CSV = "single_csv"
    ZIP_SINGLE_CSV = "zip_single_csv"
    ZIP_MULTI_CSV_JOINED = "zip_multi_csv_joined"
    ZIP_MULTI_CSV_WITH_SUPPORTING = "zip_multi_csv_with_supporting"


class InferredDType(str, Enum):
    NUMERIC_INT = "numeric_int"
    NUMERIC_FLOAT = "numeric_float"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT_FREEFORM = "text_freeform"
    UNKNOWN = "unknown"


class IngestionSummary(BaseModel):
    dataset_id: str
    source_type: SourceType
    primary_file: str
    supporting_files: List[Dict[str, Any]] = Field(default_factory=list)
    encoding: str
    encoding_confidence: float
    delimiter: str
    n_rows: int
    n_columns: int
    malformed_rows_skipped: int
    parsing_warnings: List[str] = Field(default_factory=list)


class ColumnSchema(BaseModel):
    name: str
    inferred_dtype: InferredDType
    pandas_dtype: str
    sample_values: List[Any]
    mixed_type_flag: bool = False


class DatasetSchema(BaseModel):
    columns: List[ColumnSchema]


class ColumnMissingness(BaseModel):
    missing_count: int
    missing_pct: float


class MissingnessReport(BaseModel):
    overall_missing_pct: float
    columns: Dict[str, ColumnMissingness]
    co_missing_pairs: List[Dict[str, Any]] = Field(default_factory=list)


class Histogram(BaseModel):
    bin_edges: List[float]
    counts: List[int]


class ColumnDistribution(BaseModel):
    count: int
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    median: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    histogram: Optional[Histogram] = None


class DistributionsReport(BaseModel):
    columns: Dict[str, ColumnDistribution]


class ColumnCardinality(BaseModel):
    n_unique: int
    unique_ratio: float
    high_cardinality: bool
    top_values: Dict[str, int]


class CardinalityReport(BaseModel):
    columns: Dict[str, ColumnCardinality]


class CorrelationPair(BaseModel):
    col1: str
    col2: str
    corr: float


class CorrelationReport(BaseModel):
    method: str
    matrix: Dict[str, Dict[str, float]]
    high_correlation_pairs: List[CorrelationPair]


class TargetCandidate(BaseModel):
    column: str
    score: float
    reasoning: str


class TargetDetectionReport(BaseModel):
    suggested_target: Optional[str]
    confidence: float
    reasoning: str
    task_type_guess: Optional[str] = None  # "classification" | "regression"
    candidates: List[TargetCandidate]


class DuplicatesReport(BaseModel):
    exact_duplicate_rows: int
    duplicate_pct: float
    duplicate_row_indices: List[int]


class IsolationForestReport(BaseModel):
    contamination: float
    dataset_anomaly_rate: float
    flagged_row_indices: List[int]
    column_involvement: Dict[str, int]


class DistanceBaselineReport(BaseModel):
    method: str
    threshold: float
    flagged_row_indices: List[int]


class OutlierReport(BaseModel):
    isolation_forest: Optional[IsolationForestReport] = None
    distance_baseline: Optional[DistanceBaselineReport] = None
    agreement_rate: Optional[float] = None
    note: Optional[str] = None


class SurrogateSignalReport(BaseModel):
    model: str = "lightgbm"
    ran: bool
    target_used: Optional[str] = None
    task_type: Optional[str] = None
    importances: Dict[str, float] = Field(default_factory=dict)
    note: Optional[str] = None


class ReportMeta(BaseModel):
    generated_at: str
    engine_version: str = "1.0.0"
    processing_time_seconds: float


class DatasetHealthReport(BaseModel):
    """The single artifact every downstream module (Persons 2-4) consumes."""
    dataset_id: str
    job_id: str
    status: JobStatus
    ingestion: IngestionSummary
    schema_: DatasetSchema = Field(alias="schema")
    missingness: MissingnessReport
    distributions: DistributionsReport
    cardinality: CardinalityReport
    correlation: CorrelationReport
    target_detection: TargetDetectionReport
    duplicates: DuplicatesReport
    outliers: OutlierReport
    feature_importance_signal: SurrogateSignalReport
    meta: ReportMeta

    model_config = {"populate_by_name": True}


class JobRecord(BaseModel):
    job_id: str
    dataset_id: Optional[str] = None
    status: JobStatus
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
