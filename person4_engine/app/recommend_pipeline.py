"""
recommend_pipeline.py — Main execution pipeline for Person 4 algorithm recommendation job.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app import recommend_config as config
from app.apply_client import resolve_processed_dataset
from app.benchmarker import benchmark_top_recommendations
from app.meta_features import extract_meta_features
from app.recommend_engine import rank_recommendations
from app.recommend_schemas import MetaFeatures, RecommendationReport, JobStatus


def run_recommend_job(
    dataset_id: str,
    job_id: str,
    apply_job_id: Optional[str] = None,
    target_column: Optional[str] = None,
    perform_benchmark: bool = True,
    top_k_benchmark: int = 3,
    custom_meta_features: Optional[Dict[str, Any]] = None,
) -> dict:
    start_time = time.time()

    # 1. Resolve dataset
    df, meta_info = resolve_processed_dataset(dataset_id, apply_job_id=apply_job_id)

    # 2. Extract or override meta-features
    if custom_meta_features:
        meta_feat = MetaFeatures(**custom_meta_features)
    else:
        meta_feat = extract_meta_features(df, target_col=target_column)

    # 3. Score & rank candidate algorithms
    recommendations = rank_recommendations(meta_feat)

    # 4. Optional empirical benchmarking
    if perform_benchmark and meta_feat.target_column and meta_feat.target_column in df.columns:
        recommendations = benchmark_top_recommendations(
            recommendations=recommendations,
            df=df,
            mf=meta_feat,
            top_k=top_k_benchmark
        )
        benchmarked = True
    else:
        benchmarked = False

    elapsed = round(time.time() - start_time, 3)

    report = RecommendationReport(
        status=JobStatus.SUCCESS,
        job_id=job_id,
        dataset_id=dataset_id,
        apply_job_id=apply_job_id,
        task_type=meta_feat.task_type,
        target_column=meta_feat.target_column,
        dataset_meta_features=meta_feat,
        recommendations=recommendations,
        benchmarked=benchmarked,
        meta={
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": config.ENGINE_VERSION,
            "processing_time_seconds": elapsed,
            "dataset_source": meta_info.get("source", "unknown"),
        }
    )

    report_dict = report.model_dump()

    # Persist report
    out_path = config.RECOMMENDATIONS_DIR / f"{job_id}.json"
    out_path.write_text(json.dumps(report_dict, indent=2, default=str))

    return report_dict
