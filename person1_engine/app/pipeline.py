"""
pipeline.py — glues every module together into the one artifact the rest
of the team depends on: the Dataset Health Report.

Two entry points:
  - ingest_upload(raw_bytes, filename)        -> fast, synchronous, called by /upload
  - run_full_analysis(dataset_id)             -> slow, runs in the job queue, called by /analyze
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pandas as pd

from app import config
from app.analysis.cardinality import analyze_cardinality
from app.analysis.correlation import analyze_correlation
from app.analysis.distributions import analyze_distributions
from app.analysis.missingness import analyze_missingness, detect_duplicates
from app.analysis.target_detection import detect_target
from app.ingestion.dtype_inference import infer_all_dtypes
from app.ingestion.loader import load_upload
from app.outliers.distance_baseline import compute_agreement, run_distance_baseline
from app.outliers.isolation_forest import run_isolation_forest
from app.schemas import InferredDType
from app.surrogate.lightgbm_signal import run_surrogate_signal


def _dataset_path(dataset_id: str) -> Path:
    return config.DATASETS_DIR / f"{dataset_id}.parquet"


def _ingestion_meta_path(dataset_id: str) -> Path:
    return config.DATASETS_DIR / f"{dataset_id}.meta.json"


def ingest_upload(raw_bytes: bytes, filename: str) -> dict:
    """Fast path used directly by POST /upload. Parses the file, infers
    dtypes, stores the DataFrame to disk, and returns a lightweight summary
    immediately — the expensive statistical work happens later in /analyze."""
    load_result = load_upload(raw_bytes, filename)
    dataset_id = str(uuid.uuid4())

    load_result.df.to_parquet(_dataset_path(dataset_id), index=True)

    column_infos = infer_all_dtypes(load_result.df)

    ingestion_summary = {
        "dataset_id": dataset_id,
        "source_type": load_result.source_type,
        "primary_file": load_result.primary_file,
        "supporting_files": load_result.supporting_files,
        "encoding": load_result.encoding,
        "encoding_confidence": load_result.encoding_confidence,
        "delimiter": load_result.delimiter,
        "n_rows": int(len(load_result.df)),
        "n_columns": int(len(load_result.df.columns)),
        "malformed_rows_skipped": load_result.malformed_rows_skipped,
        "parsing_warnings": load_result.warnings,
    }

    import json

    _ingestion_meta_path(dataset_id).write_text(
        json.dumps({"ingestion": ingestion_summary, "schema": {"columns": column_infos}}, default=str, indent=2)
    )

    return {
        "dataset_id": dataset_id,
        "ingestion": ingestion_summary,
        "schema": {"columns": column_infos},
    }


def run_full_analysis(dataset_id: str, job_id: str) -> dict:
    """Slow path, meant to be handed to the job queue (see app/main.py).
    Runs every statistical/ML step and assembles the final Dataset Health
    Report exactly matching app.schemas.DatasetHealthReport."""
    start = time.time()

    df = pd.read_parquet(_dataset_path(dataset_id))

    import json

    meta = json.loads(_ingestion_meta_path(dataset_id).read_text())
    ingestion_summary = meta["ingestion"]
    column_infos = meta["schema"]["columns"]
    column_dtypes: Dict[str, InferredDType] = {c["name"]: InferredDType(c["inferred_dtype"]) for c in column_infos}

    missingness = analyze_missingness(df)
    distributions = analyze_distributions(df, column_dtypes)
    cardinality = analyze_cardinality(df)
    correlation = analyze_correlation(df, column_dtypes)
    target_detection = detect_target(df, column_dtypes)
    duplicates = detect_duplicates(df)

    if_result = run_isolation_forest(df, column_dtypes)
    baseline_result = run_distance_baseline(df, column_dtypes)
    outliers = {
        "isolation_forest": if_result,
        "distance_baseline": baseline_result,
        "agreement_rate": compute_agreement(if_result, baseline_result),
        "note": None if (if_result and baseline_result) else "Skipped: fewer than 10 rows or no numeric columns.",
    }

    surrogate = run_surrogate_signal(
        df,
        column_dtypes,
        target_detection.get("suggested_target"),
        target_detection.get("task_type_guess"),
    )

    report = {
        "dataset_id": dataset_id,
        "job_id": job_id,
        "status": "success",
        "ingestion": ingestion_summary,
        "schema": {"columns": column_infos},
        "missingness": missingness,
        "distributions": distributions,
        "cardinality": cardinality,
        "correlation": correlation,
        "target_detection": target_detection,
        "duplicates": duplicates,
        "outliers": outliers,
        "feature_importance_signal": surrogate,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": config.ENGINE_VERSION,
            "processing_time_seconds": round(time.time() - start, 3),
        },
    }

    report_path = config.REPORTS_DIR / f"{job_id}.json"
    report_path.write_text(json.dumps(report, default=str, indent=2))

    return report
