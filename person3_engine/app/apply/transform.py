"""transform.py — applies Person 2's `transform` suggestions.

params: {"function": "log1p"|"yeo_johnson"}
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats


def apply_transform(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    function = suggestion.get("params", {}).get("function", "log1p")
    columns = suggestion["target_columns"]

    actions = []
    for col in columns:
        # Real messy data can have a nominally-numeric column with stray
        # non-numeric entries (Person 1's mixed_type_flag) — coerce first so
        # junk values become NaN (left untransformed) rather than crashing.
        values = pd.to_numeric(df[col], errors="coerce")

        if function == "log1p":
            df[col] = np.log1p(values.clip(lower=0))
            actions.append(f"log1p-transformed '{col}'")
        elif function == "yeo_johnson":
            mask = values.notna()
            transformed, _lambda = stats.yeojohnson(values[mask].to_numpy())
            df[col] = values
            df.loc[mask, col] = transformed
            actions.append(f"Yeo-Johnson-transformed '{col}' (lambda={_lambda:.3f})")
        else:
            raise ValueError(f"Unknown transform function {function!r}")

    return df, "; ".join(actions)
