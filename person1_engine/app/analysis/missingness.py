from __future__ import annotations

from itertools import combinations
from typing import List

import pandas as pd


def analyze_missingness(df: pd.DataFrame, top_n_pairs: int = 10) -> dict:
    n_rows = len(df)
    columns = {}
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        columns[col] = {
            "missing_count": missing_count,
            "missing_pct": round(100 * missing_count / n_rows, 3) if n_rows else 0.0,
        }

    overall_missing_pct = round(100 * df.isna().sum().sum() / (n_rows * max(len(df.columns), 1)), 3) if n_rows else 0.0

    # Co-missingness: columns whose null-masks are correlated -> often signals
    # a structural pattern (e.g. "shipping_date" only missing when "shipped" is False).
    null_mask = df.isna()
    cols_with_missing = [c for c in df.columns if null_mask[c].any()]
    co_missing_pairs: List[dict] = []
    for c1, c2 in combinations(cols_with_missing, 2):
        both = int((null_mask[c1] & null_mask[c2]).sum())
        if both == 0:
            continue
        jaccard = both / max(int((null_mask[c1] | null_mask[c2]).sum()), 1)
        co_missing_pairs.append({"col1": c1, "col2": c2, "co_missing_rows": both, "jaccard": round(jaccard, 3)})
    co_missing_pairs.sort(key=lambda p: p["jaccard"], reverse=True)

    return {
        "overall_missing_pct": overall_missing_pct,
        "columns": columns,
        "co_missing_pairs": co_missing_pairs[:top_n_pairs],
    }


def detect_duplicates(df: pd.DataFrame) -> dict:
    """Exact duplicate row detection via row hashing (fast even on wide frames)."""
    if df.empty:
        return {"exact_duplicate_rows": 0, "duplicate_pct": 0.0, "duplicate_row_indices": []}

    row_hashes = pd.util.hash_pandas_object(df, index=False)
    is_dup = row_hashes.duplicated(keep="first")
    dup_indices = df.index[is_dup].tolist()
    return {
        "exact_duplicate_rows": int(is_dup.sum()),
        "duplicate_pct": round(100 * is_dup.sum() / len(df), 3),
        "duplicate_row_indices": [int(i) for i in dup_indices[:1000]],  # cap payload size
    }
