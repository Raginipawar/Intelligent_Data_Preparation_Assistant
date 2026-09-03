"""
transform_rules.py — skew-driven log/power transform suggestions, from Person 1's
`distributions` section. log1p is preferred when valid (min >= 0); Yeo-Johnson is
used for columns containing negative values, since plain log is undefined there.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import config
from app.schemas import Suggestion, SuggestionType


def build_transform_suggestions(distributions: Dict[str, Any]) -> List[Suggestion]:
    suggestions: List[Suggestion] = []

    for col, dist in (distributions.get("columns", {}) or {}).items():
        skew = dist.get("skewness")
        if skew is None or abs(skew) < config.SKEW_TRANSFORM_THRESHOLD:
            continue

        direction = "right" if skew > 0 else "left"
        min_val = dist.get("min")

        if min_val is not None and min_val >= 0:
            func = "log1p"
            reasoning = (
                f"'{col}' is {direction}-skewed (skewness={skew:.2f}); a log1p transform will compress "
                "the long tail and move the distribution closer to normal, which helps linear and "
                "distance-based models that assume roughly-normal inputs."
            )
        else:
            func = "yeo_johnson"
            reasoning = (
                f"'{col}' is {direction}-skewed (skewness={skew:.2f}) and contains negative values "
                f"(min={min_val}), so a Yeo-Johnson power transform is suggested instead of log "
                "(plain log is undefined for non-positive input)."
            )

        confidence = round(min(0.95, 0.5 + abs(skew) / 10), 3)
        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.TRANSFORM,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact=f"Reduces |skewness| of '{col}' from {abs(skew):.2f} toward 0",
                params={"function": func},
                confidence=confidence,
            )
        )

    return suggestions
