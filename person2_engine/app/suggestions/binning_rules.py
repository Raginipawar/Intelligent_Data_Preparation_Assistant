"""
binning_rules.py — quantile-binning suggestions, an alternative to a log/power
transform for numeric columns that are heavily skewed but have a moderate
number of distinct values (not so many that binning loses most of the signal,
not so few it's pointless). Tree-based models in particular benefit from
binning's more even split points on heavy-tailed data.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import config
from app.schemas import Suggestion, SuggestionType


def build_binning_suggestions(distributions: Dict[str, Any], cardinality: Dict[str, Any]) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    card_columns = cardinality.get("columns", {}) or {}

    for col, dist in (distributions.get("columns", {}) or {}).items():
        skew = dist.get("skewness")
        if skew is None or abs(skew) < config.BINNING_SKEW_THRESHOLD:
            continue

        n_unique = (card_columns.get(col) or {}).get("n_unique", 0)
        if not (config.BINNING_MIN_UNIQUE <= n_unique <= config.BINNING_MAX_UNIQUE):
            continue

        reasoning = (
            f"'{col}' has {n_unique} distinct values and is heavily skewed (skewness={skew:.2f}); "
            "quantile binning into ~5 buckets is an alternative to a log/power transform that also "
            "helps tree-based models split more evenly and is more robust to extreme tail values."
        )
        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.BINNING,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact="Evens out split points for tree-based models; alternative to a monotonic transform",
                params={"strategy": "quantile", "n_bins": 5},
                confidence=0.5,
            )
        )

    return suggestions
