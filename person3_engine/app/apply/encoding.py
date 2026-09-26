"""encoding.py — applies Person 2's `encoding` suggestions.

params: {"method": "onehot"|"frequency"|"target", "smoothing"?: "cv_smoothed"}

Person 2 already decided the encoding strategy (including running its own
cross-validated fit for target encoding); at apply time we don't re-run CV —
we do a single global fit against the (already imputed) column, which is the
standard "apply the chosen recipe" step this layer owns. Target encoding needs
a target column: if none is resolvable, this degrades to frequency encoding
rather than failing outright, and says so in the action log.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd


def _onehot(df: pd.DataFrame, col: str) -> Tuple[pd.DataFrame, str]:
    dummies = pd.get_dummies(df[col], prefix=col, dummy_na=False)
    df = df.drop(columns=[col]).join(dummies)
    return df, f"one-hot encoded '{col}' into {list(dummies.columns)}"


def _frequency(df: pd.DataFrame, col: str) -> Tuple[pd.DataFrame, str]:
    freq = df[col].value_counts(normalize=True)
    df[col] = df[col].map(freq).astype(float)
    return df, f"frequency-encoded '{col}' in place"


def _target(df: pd.DataFrame, col: str, target_col: Optional[str]) -> Tuple[pd.DataFrame, str]:
    if target_col is None or target_col not in df.columns or target_col == col:
        df, action = _frequency(df, col)
        return df, f"{action} (target encoding requested but no usable target column available)"

    target_numeric = pd.to_numeric(df[target_col], errors="coerce")
    global_mean = target_numeric.mean()
    means = target_numeric.groupby(df[col]).mean()
    df[col] = df[col].map(means).fillna(global_mean).astype(float)
    return df, f"target-encoded '{col}' against '{target_col}'"


def apply_encoding(df: pd.DataFrame, suggestion: Dict[str, Any], target_col: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    method = suggestion.get("params", {}).get("method", "frequency")
    actions = []
    for col in suggestion["target_columns"]:
        if method == "onehot":
            df, action = _onehot(df, col)
        elif method == "target":
            df, action = _target(df, col, target_col)
        elif method == "frequency":
            df, action = _frequency(df, col)
        else:
            raise ValueError(f"Unknown encoding method {method!r}")
        actions.append(action)
    return df, "; ".join(actions)
