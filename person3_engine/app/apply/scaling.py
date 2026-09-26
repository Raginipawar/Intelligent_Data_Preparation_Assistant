"""scaling.py — applies Person 2's `scaling` suggestions.

params: {"method": "standard"|"robust"}

Computed directly with pandas (not sklearn's StandardScaler/RobustScaler,
which reject NaN outright) so a column with leftover missing values — or
stray non-numeric entries from Person 1's mixed_type_flag columns — degrades
to "left as NaN" for those cells instead of crashing the whole suggestion.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd


def apply_scaling(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    method = suggestion.get("params", {}).get("method", "standard")
    if method not in ("standard", "robust"):
        raise ValueError(f"Unknown scaling method {method!r}")
    columns = suggestion["target_columns"]

    for col in columns:
        values = pd.to_numeric(df[col], errors="coerce")
        if method == "standard":
            center, spread = values.mean(), values.std()
        else:
            center, spread = values.median(), values.quantile(0.75) - values.quantile(0.25)
        df[col] = (values - center) / spread if spread not in (0, None) else values - center

    return df, f"{method}-scaled {columns}"
