"""
redundancy.py — every suggestion of type `drop_redundant`, from two distinct
signals in Person 1's report:

1. Correlated-feature clusters: build a minimum spanning tree over numeric
   columns using Person 1's Pearson correlation matrix, weight = 1 - |corr|
   (see _graph_utils.py). Cut MST edges below REDUNDANCY_CORR_THRESHOLD,
   leaving connected components that are pairwise-connected via strong
   correlation — each such cluster is redundant; keep the member with the
   highest LightGBM feature-importance (Person 1's surrogate signal), falling
   back to highest variance, and suggest dropping the rest.

2. Near-unique "identifier" columns: Person 1's own `high_cardinality` flag
   (cardinality.py) is deliberately strict — unique_ratio >= 0.9 AND
   n_unique > 20 — tuned to catch row/transaction IDs rather than merely
   inconvenient categoricals. A column that trips it is almost never a
   generalizable feature, so it's suggested for an outright drop rather than
   being routed to encoding_rules.py (which explicitly skips these columns).
   Continuous numeric_float columns are excluded from this check — a
   near-unique 'price' column is a legitimate feature, not an identifier.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app import suggestion_config as config
from app.suggestion_schemas import Suggestion, SuggestionType
from app.suggestions._graph_utils import build_mst_edges, connected_components

_IDENTIFIER_CANDIDATE_DTYPES = {"categorical", "numeric_int", "text_freeform"}


def _pick_keeper(cluster: List[str], importances: Dict[str, float], distributions: Dict[str, Any]) -> str:
    if importances:
        scored = sorted(((c, importances.get(c, 0.0)) for c in cluster), key=lambda x: x[1], reverse=True)
        if scored[0][1] > 0:
            return scored[0][0]
    dist_columns = distributions.get("columns", {}) or {}
    scored = sorted(((c, (dist_columns.get(c) or {}).get("std") or 0.0) for c in cluster), key=lambda x: x[1], reverse=True)
    if scored and scored[0][1] > 0:
        return scored[0][0]
    return sorted(cluster)[0]


def build_correlated_cluster_suggestions(
    correlation: Dict[str, Any],
    feature_importance_signal: Dict[str, Any],
    distributions: Dict[str, Any],
) -> List[Suggestion]:
    matrix: Dict[str, Dict[str, float]] = correlation.get("matrix", {}) or {}
    columns = list(matrix.keys())
    if len(columns) < 2:
        return []

    mst_edges = build_mst_edges(columns, matrix)
    strong_edges = [(a, b, corr) for a, b, corr in mst_edges if abs(corr) >= config.REDUNDANCY_CORR_THRESHOLD]
    if not strong_edges:
        return []

    clusters = connected_components(columns, strong_edges)
    importances = (feature_importance_signal or {}).get("importances") or {}

    suggestions: List[Suggestion] = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        keeper = _pick_keeper(cluster, importances, distributions)
        drop_cols = [c for c in cluster if c != keeper]
        cluster_set = set(cluster)
        max_corr = max((abs(corr) for a, b, corr in strong_edges if a in cluster_set and b in cluster_set), default=0.0)
        why_kept = "highest LightGBM feature importance in the cluster" if importances else "highest variance in the cluster"

        reasoning = (
            f"Columns {sorted(cluster)} form a highly correlated cluster (max pairwise |r|={max_corr:.2f}, "
            f">= threshold {config.REDUNDANCY_CORR_THRESHOLD}); keeping '{keeper}' ({why_kept}) and "
            "dropping the rest to reduce multicollinearity and redundant dimensionality."
        )
        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.DROP_REDUNDANT,
                target_columns=drop_cols,
                reasoning=reasoning,
                expected_impact=f"Removes {len(drop_cols)} redundant column(s) with minimal information loss",
                params={"reason": "correlated_redundancy", "cluster": sorted(cluster), "kept_column": keeper, "max_abs_corr": round(max_corr, 4)},
                confidence=round(min(0.95, 0.5 + max_corr / 2), 3),
            )
        )
    return suggestions


def build_identifier_drop_suggestions(
    cardinality: Dict[str, Any],
    schema_columns: List[Dict[str, Any]],
    target_col: Optional[str],
) -> List[Suggestion]:
    dtype_map = {c["name"]: c.get("inferred_dtype") for c in schema_columns}
    card_columns = cardinality.get("columns", {}) or {}

    suggestions: List[Suggestion] = []
    for col, card in card_columns.items():
        if col == target_col or not card.get("high_cardinality"):
            continue
        if dtype_map.get(col) not in _IDENTIFIER_CANDIDATE_DTYPES:
            continue

        reasoning = (
            f"'{col}' has a unique_ratio of {card.get('unique_ratio')} ({card.get('n_unique')} unique values) "
            "— Person 1's high-cardinality flag (unique_ratio >= 0.9 and > 20 unique values) suggests this "
            "is closer to an identifier (row ID, transaction ID, free-text key) than a generalizable feature. "
            "Suggest dropping it before modeling."
        )
        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.DROP_REDUNDANT,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact="Removes a likely non-generalizable identifier column",
                params={"reason": "high_cardinality_identifier"},
                confidence=0.6,
            )
        )
    return suggestions


def build_redundancy_suggestions(
    correlation: Dict[str, Any],
    feature_importance_signal: Dict[str, Any],
    distributions: Dict[str, Any],
    cardinality: Dict[str, Any],
    schema_columns: List[Dict[str, Any]],
    target_col: Optional[str],
) -> List[Suggestion]:
    return build_correlated_cluster_suggestions(
        correlation, feature_importance_signal, distributions
    ) + build_identifier_drop_suggestions(cardinality, schema_columns, target_col)
