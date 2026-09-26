"""feature_selection.py — budget-constrained feature selection: given a limit
on final feature count, trims the *least* valuable columns first.

Runs after every suggestion has been applied, using a `column_registry` the
orchestrator builds while applying (tier + confidence per engineered/touched
column — raw, untouched original columns are never registered and are always
tier 0, i.e. kept preferentially).

Tiers (higher tier = dropped first):
  3 — interaction-created columns (purely derived, most disposable)
  2 — binning-created columns (an alternative representation, not essential)
  1 — one-hot dummy columns (fine-grained; individual dummies are cheap to drop)
  0 — everything else (raw original columns, or columns modified in place by
      imputation/scaling/transform/encoding — never trimmed by this step)

Within a tier, columns from the lowest-`confidence` suggestion are dropped
first. If the budget still isn't met after every tier-1..3 candidate is gone,
trimming stops there rather than touching tier-0 (raw/original) columns —
Person 3 won't silently destroy data the user never asked to engineer away.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def apply_feature_budget(
    df: pd.DataFrame,
    column_registry: Dict[str, Dict[str, Any]],
    feature_budget: Optional[int],
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    if feature_budget is None or len(df.columns) <= feature_budget:
        return df, []

    droppable = [c for c in df.columns if column_registry.get(c, {}).get("tier", 0) > 0]
    droppable.sort(
        key=lambda c: (
            -column_registry[c]["tier"],
            column_registry[c].get("confidence", 1.0),
        )
    )

    log_entries: List[Dict[str, Any]] = []
    for col in droppable:
        if len(df.columns) <= feature_budget:
            break
        tier = column_registry[col]["tier"]
        source = column_registry[col].get("source_suggestion_id", "?")
        df = df.drop(columns=[col])
        log_entries.append(
            {
                "column": col,
                "reasoning": (
                    f"Dropped '{col}' (tier {tier}, from suggestion '{source}') to satisfy "
                    f"feature_budget={feature_budget}."
                ),
            }
        )

    if len(df.columns) > feature_budget:
        log_entries.append(
            {
                "column": None,
                "reasoning": (
                    f"feature_budget={feature_budget} could not be fully satisfied without dropping "
                    f"original/raw columns ({len(df.columns)} remain) — stopped trimming rather than "
                    "removing data the user never asked to engineer away."
                ),
            }
        )

    return df, log_entries
