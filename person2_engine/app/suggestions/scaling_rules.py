"""
scaling_rules.py — scaling-method suggestions for numeric columns, driven by
Person 1's `distributions` section (for which columns are numeric at all) and
`outliers.isolation_forest.column_involvement` (which numeric columns actually
drive flagged anomaly rows, per z-score contribution).

A column with real outlier involvement gets RobustScaler (median/IQR-based,
insensitive to extreme values); everything else defaults to StandardScaler.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.schemas import Suggestion, SuggestionType


def build_scaling_suggestions(distributions: Dict[str, Any], outliers: Dict[str, Any]) -> List[Suggestion]:
    suggestions: List[Suggestion] = []

    involvement: Dict[str, int] = {}
    if outliers and outliers.get("isolation_forest"):
        involvement = outliers["isolation_forest"].get("column_involvement", {}) or {}

    for col, dist in (distributions.get("columns", {}) or {}).items():
        std = dist.get("std")
        if std is None or std == 0:
            continue  # constant/degenerate column — scaling is meaningless

        outlier_hits = involvement.get(col, 0)
        if outlier_hits > 0:
            params = {"method": "robust"}
            reasoning = (
                f"'{col}' is involved in {outlier_hits} isolation-forest-flagged outlier row(s) "
                "(per Person 1's column-involvement scoring). RobustScaler (median/IQR-based) is "
                "less sensitive to those outliers than StandardScaler, which uses mean/std and would "
                "let a handful of extreme values distort the scale for every other row."
            )
            confidence = 0.75
        else:
            params = {"method": "standard"}
            reasoning = (
                f"'{col}' shows no notable outlier involvement in Person 1's isolation-forest pass; "
                "StandardScaler (zero mean, unit variance) is a safe default for scale-sensitive models."
            )
            confidence = 0.6

        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.SCALING,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact=f"Puts '{col}' on a comparable scale to other features ({params['method']} scaling)",
                params=params,
                confidence=confidence,
            )
        )

    return suggestions
