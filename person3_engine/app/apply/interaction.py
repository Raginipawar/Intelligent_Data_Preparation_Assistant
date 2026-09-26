"""interaction.py — applies Person 2's `interaction` suggestions.

params: {"operation": "multiply", "new_column": "a_x_b"}
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd


def apply_interaction(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    params = suggestion.get("params", {})
    operation = params.get("operation", "multiply")
    columns = suggestion["target_columns"]
    new_column = params.get("new_column") or "_x_".join(columns)

    if operation != "multiply":
        raise ValueError(f"Unknown interaction operation {operation!r}")
    if len(columns) != 2:
        raise ValueError(f"Multiplicative interaction requires exactly 2 target_columns, got {columns!r}")

    a, b = columns
    # Coerce rather than astype(float): a nominally-numeric column can carry
    # stray non-numeric entries (Person 1's mixed_type_flag) — those become
    # NaN in the product instead of crashing the whole suggestion.
    df[new_column] = pd.to_numeric(df[a], errors="coerce") * pd.to_numeric(df[b], errors="coerce")

    return df, f"added '{new_column}' = '{a}' * '{b}'"
