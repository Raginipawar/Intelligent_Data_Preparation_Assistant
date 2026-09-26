"""drop_redundant.py — applies Person 2's `drop_redundant` suggestions.

params: {"reason": "correlated_redundancy"|"high_cardinality_identifier",
         "cluster"?: [...], "kept_column"?: "..."}

Per Person 2's README: `target_columns` lists the columns to DROP, not keep —
the survivor (if any) is in params.kept_column.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd


def apply_drop_redundant(df: pd.DataFrame, suggestion: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    columns = [c for c in suggestion["target_columns"] if c in df.columns]
    if not columns:
        return df, "nothing to drop (already absent)"

    reason = suggestion.get("params", {}).get("reason", "redundant")
    kept_column = suggestion.get("params", {}).get("kept_column")
    df = df.drop(columns=columns)

    kept_note = f", kept '{kept_column}'" if kept_column else ""
    return df, f"dropped {columns} ({reason}){kept_note}"
