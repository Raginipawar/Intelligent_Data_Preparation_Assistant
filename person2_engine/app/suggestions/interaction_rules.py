"""
interaction_rules.py — multiplicative interaction-term candidates, from Person 1's
`feature_importance_signal` (rough LightGBM importances) and `correlation` matrix.

Only fires when the surrogate model actually ran (feature_importance_signal.ran).
Considers pairs among the top-importance columns; skips pairs that are already
strongly correlated with each other (redundancy.py already suggests dropping one
of those — an interaction term built from two near-duplicate columns adds little).
Capped at INTERACTION_TOP_K pairs to avoid combinatorial suggestion spam.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import config
from app.schemas import Suggestion, SuggestionType


def build_interaction_suggestions(
    feature_importance_signal: Dict[str, Any],
    correlation: Dict[str, Any],
) -> List[Suggestion]:
    signal = feature_importance_signal or {}
    importances: Dict[str, float] = signal.get("importances") or {}
    if not signal.get("ran") or len(importances) < 2:
        return []

    ranked = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)
    pool_size = config.INTERACTION_TOP_K + 2
    top_cols = [c for c, _ in ranked[:pool_size]]
    matrix: Dict[str, Dict[str, float]] = correlation.get("matrix", {}) or {}

    suggestions: List[Suggestion] = []
    for i, a in enumerate(top_cols):
        if len(suggestions) >= config.INTERACTION_TOP_K:
            break
        for b in top_cols[i + 1 :]:
            if len(suggestions) >= config.INTERACTION_TOP_K:
                break
            corr_ab = matrix.get(a, {}).get(b)
            if corr_ab is None:
                corr_ab = matrix.get(b, {}).get(a)
            if corr_ab is not None and abs(corr_ab) >= config.INTERACTION_REDUNDANCY_CORR:
                continue  # already near-redundant — handled by redundancy.py instead

            corr_str = f"{corr_ab:.2f}" if corr_ab is not None else "n/a"
            reasoning = (
                f"'{a}' and '{b}' both rank highly in Person 1's rough LightGBM feature-importance signal "
                f"(importances {importances[a]:.3f} and {importances[b]:.3f}) but are not strongly correlated "
                f"with each other (r={corr_str}), so a multiplicative interaction term may capture a joint "
                "effect neither column expresses alone."
            )
            new_col = f"{a}_x_{b}"
            suggestions.append(
                Suggestion(
                    id="placeholder",
                    type=SuggestionType.INTERACTION,
                    target_columns=[a, b],
                    reasoning=reasoning,
                    expected_impact="Potential joint-effect signal for tree/linear models",
                    params={"operation": "multiply", "new_column": new_col},
                    confidence=0.4,
                )
            )

    return suggestions
