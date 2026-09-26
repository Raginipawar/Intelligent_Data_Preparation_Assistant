"""imputation.py — applies Person 2's `imputation` suggestions.

params: {"strategy": "mean"|"median"|"mode"|"constant", "fill_value"?: "..."}
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd


def apply_imputation(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    """Returns (mutated df, action description). Raises KeyError/ValueError on
    a malformed suggestion — the orchestrator catches and logs those."""
    columns = suggestion["target_columns"]
    strategy = suggestion.get("params", {}).get("strategy", "mean")
    fill_value = suggestion.get("params", {}).get("fill_value")

    actions = []
    for col in columns:
        series = df[col]

        if strategy in ("mean", "median"):
            # Real messy data can have a nominally-numeric column with stray
            # non-numeric entries (Person 1's mixed_type_flag). Coerce first so
            # those junk values become NaN and get imputed too, instead of
            # crashing the whole apply job on a single bad cell.
            series = pd.to_numeric(series, errors="coerce")
            value = series.mean() if strategy == "mean" else series.median()
            # numpy >=2.0 reprs a float64 scalar as "np.float64(65.04)" — fine internally,
            # but this same `value` lands in the human-readable action string below, where
            # that wrapper just looks like a bug. Cast to a plain rounded Python float first.
            if pd.notna(value):
                value = round(float(value), 4)
        elif strategy == "mode":
            modes = series.mode(dropna=True)
            value = modes.iloc[0] if not modes.empty else fill_value
        elif strategy == "constant":
            value = fill_value if fill_value is not None else "missing"
        else:
            raise ValueError(f"Unknown imputation strategy {strategy!r}")

        n_missing = int(series.isna().sum())
        df[col] = series.mask(series.isna(), value)
        actions.append(f"filled {n_missing} missing value(s) in '{col}' with {strategy} ({value!s})")

    return df, "; ".join(actions)
