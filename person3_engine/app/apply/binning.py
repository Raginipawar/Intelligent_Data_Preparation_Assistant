"""binning.py — applies Person 2's `binning` suggestions.

params: {"strategy": "quantile", "n_bins": 5}

Adds a new `{col}_binned` column rather than overwriting the original —
binning is offered as an "alternative representation" per Person 2's README,
not a replacement, so the raw column stays available for other suggestions
(e.g. scaling) applied in the same run.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd


def apply_binning(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    params = suggestion.get("params", {})
    n_bins = params.get("n_bins", 5)
    strategy = params.get("strategy", "quantile")
    if strategy != "quantile":
        raise ValueError(f"Unknown binning strategy {strategy!r}")

    actions = []
    for col in suggestion["target_columns"]:
        new_col = f"{col}_binned"
        # Coerce rather than bin the raw column: a nominally-numeric column can
        # carry stray non-numeric entries (Person 1's mixed_type_flag) — those
        # become NaN (left unbinned) instead of crashing qcut outright.
        values = pd.to_numeric(df[col], errors="coerce")
        if values.nunique(dropna=True) < 2:
            # qcut can't form any bin edges from a single distinct value —
            # everything trivially belongs to the one bin that exists.
            df[new_col] = 0
            actions.append(f"added '{new_col}' (single bin — '{col}' has fewer than 2 distinct values)")
            continue
        # duplicates="drop" collapses bin edges that coincide (low-cardinality
        # numeric columns), so this yields at most n_bins actual bins.
        df[new_col] = pd.qcut(values, q=n_bins, labels=False, duplicates="drop")
        actions.append(f"added '{new_col}' ({n_bins}-bin quantile binning of '{col}')")

    return df, "; ".join(actions)
