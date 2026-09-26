"""
apply_pipeline.py — the job-queue entry point handed to the shared queue by
POST /apply (app/apply_api.py). Resolves the raw dataset + suggestion list,
runs the orchestrator, persists the processed dataset the same way Person 1
persists its report and Person 2 persists its suggestion list — this engine's
storage/applied folder is self-contained and never writes into the other two
engines' storage.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import apply_config as config
from app.apply.orchestrator import run_orchestration
from app.dataset_client import resolve_dataset
from app.suggestion_client import resolve_suggestions


def _applied_dataset_path(job_id: str) -> Path:
    return config.APPLIED_DIR / f"{job_id}.parquet"


def _applied_meta_path(job_id: str) -> Path:
    return config.APPLIED_DIR / f"{job_id}.meta.json"


def run_apply_job(
    dataset_id: str,
    job_id: str,
    selected_suggestion_ids: List[str],
    source_job_id: Optional[str] = None,
    inline_suggestions: Optional[List[Dict[str, Any]]] = None,
    feature_budget: Optional[int] = None,
    target_column: Optional[str] = None,
) -> dict:
    start = time.time()

    df, source_type, primary_file = resolve_dataset(dataset_id)
    suggestions = resolve_suggestions(source_job_id, inline_suggestions)

    result = run_orchestration(
        df=df,
        all_suggestions=suggestions,
        selected_suggestion_ids=selected_suggestion_ids,
        feature_budget=feature_budget,
        target_col=target_column,
    )
    final_df = result["df"]

    final_df.to_parquet(_applied_dataset_path(job_id), index=True)
    _applied_meta_path(job_id).write_text(
        json.dumps({"dataset_id": dataset_id, "source_type": source_type, "primary_file": primary_file}, indent=2)
    )

    report = {
        "dataset_id": dataset_id,
        "apply_job_id": job_id,
        "source_job_id": source_job_id,
        "status": "success",
        "applied_suggestions": result["applied_suggestions"],
        "skipped_suggestions": result["skipped_suggestions"],
        "transformation_log": result["transformation_log"],
        "final_columns": list(final_df.columns),
        "n_rows": int(len(final_df)),
        "n_columns": int(len(final_df.columns)),
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": config.ENGINE_VERSION,
            "processing_time_seconds": round(time.time() - start, 3),
        },
    }

    output_path = config.APPLIED_DIR / f"{job_id}.json"
    output_path.write_text(json.dumps(report, default=str, indent=2))

    return report
