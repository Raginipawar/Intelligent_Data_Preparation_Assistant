"""
pipeline.py — the orchestration entry point handed to the job queue by
POST /suggest (app/suggestion_api.py). Resolves inputs via health_report_client, runs the
suggestion engine, and persists the result the same way Person 1's pipeline
persists the Dataset Health Report — so this engine's storage/suggestions
folder is self-contained and never writes into Person 1's storage.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app import suggestion_config as config
from app.health_report_client import resolve_health_report, try_load_raw_dataset
from app.suggestions.suggestion_builder import generate_suggestions


def run_suggestion_job(
    dataset_id: str,
    job_id: str,
    source_job_id: Optional[str] = None,
    inline_report: Optional[Dict[str, Any]] = None,
) -> dict:
    health_report = resolve_health_report(dataset_id, source_job_id, inline_report)
    df = try_load_raw_dataset(dataset_id)

    result = generate_suggestions(
        health_report=health_report,
        df=df,
        dataset_id=dataset_id,
        source_job_id=source_job_id,
        job_id=job_id,
    )

    output_path = config.SUGGESTIONS_DIR / f"{job_id}.json"
    output_path.write_text(json.dumps(result, default=str, indent=2))

    return result
