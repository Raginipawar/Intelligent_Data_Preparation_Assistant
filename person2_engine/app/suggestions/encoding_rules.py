"""
encoding_rules.py — encoding-method suggestions for categorical columns, driven
by Person 1's `cardinality` + `target_detection` sections.

Note on thresholds: Person 1's own `high_cardinality` flag (cardinality.py) is
deliberately strict (unique_ratio >= 0.9 AND n_unique > 20) — tuned to catch
near-unique identifier columns, not "merely inconvenient for one-hot" columns.
A 200-category column out of 50,000 rows (ratio 0.004) would NOT trip that flag
but would still blow up one-hot into 200 sparse dimensions. So encoding method
here uses its own, more practical n_unique threshold
(config.LOW_CARDINALITY_ONEHOT_MAX); Person 1's stricter flag is instead used in
redundancy.py to suggest dropping likely-identifier columns outright — a column
already flagged there is skipped here to avoid emitting contradictory
"encode this" and "drop this" suggestions for the same column.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import config
from app.schemas import Suggestion, SuggestionType


def build_encoding_suggestions(
    cardinality: Dict[str, Any],
    schema_columns: List[Dict[str, Any]],
    target_detection: Dict[str, Any],
) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    categorical_cols = [c["name"] for c in schema_columns if c.get("inferred_dtype") == "categorical"]
    target_col = (target_detection or {}).get("suggested_target")
    card_columns = cardinality.get("columns", {}) or {}

    for col in categorical_cols:
        if col == target_col:
            continue
        card = card_columns.get(col, {})
        if card.get("high_cardinality"):
            # Likely an identifier column — handled as a drop suggestion in
            # redundancy.py's build_identifier_drop_suggestions, not here.
            continue

        n_unique = card.get("n_unique", 0)
        unique_ratio = card.get("unique_ratio", 0.0)

        if n_unique <= config.LOW_CARDINALITY_ONEHOT_MAX:
            params = {"method": "onehot"}
            reasoning = (
                f"'{col}' has only {n_unique} unique values — low enough for one-hot encoding "
                "without excessive dimensionality growth."
            )
            confidence = 0.85
        elif target_col:
            params = {"method": "target", "smoothing": "cv_smoothed"}
            reasoning = (
                f"'{col}' has {n_unique} unique values (unique_ratio={unique_ratio:.3f}) — too many for "
                f"one-hot without exploding dimensionality. A target column ('{target_col}') was detected, "
                "so cross-validated / smoothed target encoding is suggested over one-hot; use CV folds or "
                "leave-one-out smoothing when applying this to avoid target leakage."
            )
            confidence = 0.7
        else:
            params = {"method": "frequency"}
            reasoning = (
                f"'{col}' has {n_unique} unique values (unique_ratio={unique_ratio:.3f}) — too many for "
                "one-hot. No reliable target column was detected, so frequency encoding (each category "
                "replaced by its occurrence count/rate) is suggested instead of target encoding."
            )
            confidence = 0.65

        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.ENCODING,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact=f"Makes '{col}' model-ready ({n_unique} categories -> {params['method']} encoding)",
                params=params,
                confidence=confidence,
            )
        )

    return suggestions
