from __future__ import annotations

from itertools import combinations

import pandas as pd

from app.schemas import InferredDType


def analyze_correlation(df: pd.DataFrame, column_dtypes: dict, high_corr_threshold: float = 0.75) -> dict:
    numeric_cols = [
        c for c, dt in column_dtypes.items() if dt in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT)
    ]
    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce") if numeric_cols else pd.DataFrame()

    if numeric_df.shape[1] < 2:
        return {"method": "pearson", "matrix": {}, "high_correlation_pairs": []}

    corr = numeric_df.corr(method="pearson", min_periods=2).round(4)
    corr_clean = corr.where(pd.notna(corr), 0.0)
    matrix = {col: corr_clean[col].to_dict() for col in corr_clean.columns}

    high_pairs = []
    for c1, c2 in combinations(corr.columns, 2):
        val = corr.loc[c1, c2]
        if pd.notna(val) and abs(val) >= high_corr_threshold:
            high_pairs.append({"col1": c1, "col2": c2, "corr": round(float(val), 4)})
    high_pairs.sort(key=lambda p: abs(p["corr"]), reverse=True)

    return {"method": "pearson", "matrix": matrix, "high_correlation_pairs": high_pairs}
