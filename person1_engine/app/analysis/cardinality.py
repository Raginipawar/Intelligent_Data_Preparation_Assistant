from __future__ import annotations

import pandas as pd

from app import config


def analyze_cardinality(df: pd.DataFrame, top_k_values: int = 5) -> dict:
    n_rows = max(len(df), 1)
    columns = {}
    for col in df.columns:
        n_unique = int(df[col].nunique(dropna=True))
        unique_ratio = round(n_unique / n_rows, 4)
        top_values_series = df[col].value_counts(dropna=True).head(top_k_values)
        top_values = {str(k): int(v) for k, v in top_values_series.items()}
        columns[col] = {
            "n_unique": n_unique,
            "unique_ratio": unique_ratio,
            "high_cardinality": unique_ratio >= config.HIGH_CARDINALITY_RATIO_THRESHOLD and n_unique > 20,
            "top_values": top_values,
        }
    return {"columns": columns}
