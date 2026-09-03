"""
suggestion_builder.py — glues every rule module together into the one artifact
Person 3 (apply/execute layer) consumes: the ranked Suggestion List.

Entry point: generate_suggestions(health_report, df, dataset_id, source_job_id, job_id)
  - health_report: dict, Person 1's Dataset Health Report (required)
  - df: pandas DataFrame or None (optional — only used for AutoGluon enrichment)
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from app import config
from app.schemas import Suggestion, SuggestionType
from app.suggestions.automl_enrichment import run_autogluon_feature_enrichment, try_auto_sklearn_peek
from app.suggestions.binning_rules import build_binning_suggestions
from app.suggestions.encoding_rules import build_encoding_suggestions
from app.suggestions.interaction_rules import build_interaction_suggestions
from app.suggestions.missingness_rules import build_imputation_suggestions
from app.suggestions.redundancy import build_redundancy_suggestions
from app.suggestions.scaling_rules import build_scaling_suggestions
from app.suggestions.transform_rules import build_transform_suggestions

# Higher weight = considered higher-impact when confidence is equal. Combined with each
# suggestion's own `confidence` to produce priority_rank (see _rank).
_TYPE_WEIGHT = {
    SuggestionType.DROP_REDUNDANT: 1.0,
    SuggestionType.IMPUTATION: 0.9,
    SuggestionType.ENCODING: 0.8,
    SuggestionType.TRANSFORM: 0.7,
    SuggestionType.SCALING: 0.6,
    SuggestionType.BINNING: 0.4,
    SuggestionType.INTERACTION: 0.3,
}


def _make_id(seen_counts: Dict[str, int], suggestion: Suggestion) -> str:
    cols_slug = "_".join(c.lower().replace(" ", "-") for c in suggestion.target_columns) or "dataset"
    base = f"{suggestion.type.value}_{cols_slug}"
    seen_counts[base] = seen_counts.get(base, 0) + 1
    n = seen_counts[base]
    return base if n == 1 else f"{base}_{n}"


def _rank(suggestions: List[Suggestion]) -> List[Suggestion]:
    def score(s: Suggestion) -> float:
        return _TYPE_WEIGHT.get(s.type, 0.5) * s.confidence

    ordered = sorted(suggestions, key=score, reverse=True)
    for i, s in enumerate(ordered, start=1):
        s.priority_rank = i
    return ordered


def _assign_ids(suggestions: List[Suggestion]) -> List[Suggestion]:
    seen: Dict[str, int] = {}
    for s in suggestions:
        s.id = _make_id(seen, s)
    return suggestions


def _cross_check_with_autogluon(suggestions: List[Suggestion], autogluon_result: Dict[str, Any]) -> List[Suggestion]:
    if not autogluon_result or not autogluon_result.get("ran"):
        return suggestions
    dropped_by_ag = set(autogluon_result.get("columns_dropped_by_autogluon", []))
    if not dropped_by_ag:
        return suggestions
    for s in suggestions:
        if dropped_by_ag.intersection(s.target_columns):
            s.reasoning += (
                " (AutoGluon's own feature generator independently flagged this column too, "
                "corroborating this suggestion.)"
            )
            s.source = "rule_based+autogluon"
            s.confidence = round(min(0.99, s.confidence + 0.15), 3)
    return suggestions


def generate_suggestions(
    health_report: Dict[str, Any],
    df: Optional[pd.DataFrame],
    dataset_id: str,
    source_job_id: Optional[str],
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.time()
    job_id = job_id or str(uuid.uuid4())

    schema_columns = (health_report.get("schema") or health_report.get("schema_") or {}).get("columns", [])
    missingness = health_report.get("missingness", {}) or {}
    distributions = health_report.get("distributions", {}) or {}
    cardinality = health_report.get("cardinality", {}) or {}
    correlation = health_report.get("correlation", {}) or {}
    target_detection = health_report.get("target_detection", {}) or {}
    outliers = health_report.get("outliers", {}) or {}
    feature_importance_signal = health_report.get("feature_importance_signal", {}) or {}
    target_col = target_detection.get("suggested_target")

    raw: List[Suggestion] = []
    raw += build_imputation_suggestions(missingness, distributions, schema_columns)
    raw += build_encoding_suggestions(cardinality, schema_columns, target_detection)
    raw += build_scaling_suggestions(distributions, outliers)
    raw += build_transform_suggestions(distributions)
    raw += build_redundancy_suggestions(
        correlation, feature_importance_signal, distributions, cardinality, schema_columns, target_col
    )
    raw += build_binning_suggestions(distributions, cardinality)
    raw += build_interaction_suggestions(feature_importance_signal, correlation)

    enrichment: Dict[str, Any] = {}
    if config.AUTOGLUON_ENRICHMENT_ENABLED:
        enrichment["autogluon"] = run_autogluon_feature_enrichment(df)
        enrichment["auto_sklearn"] = try_auto_sklearn_peek()
        raw = _cross_check_with_autogluon(raw, enrichment["autogluon"])

    ranked = _rank(raw)
    ranked = _assign_ids(ranked)

    return {
        "dataset_id": dataset_id,
        "source_job_id": source_job_id,
        "job_id": job_id,
        "status": "success",
        "suggestions": [s.model_dump(mode="json") for s in ranked],
        "automl_enrichment": enrichment,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": config.ENGINE_VERSION,
            "processing_time_seconds": round(time.time() - start, 3),
        },
    }
