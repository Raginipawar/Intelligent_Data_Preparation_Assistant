from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from app import config
from app.schemas import InferredDType


def run_distance_baseline(df: pd.DataFrame, column_dtypes: Dict[str, InferredDType]) -> dict:
    """Deliberately simple: standardize numeric columns, compute each row's
    Euclidean distance from the centroid, flag rows above a percentile
    threshold. This is the naive comparison point for Isolation Forest —
    it has no notion of density or local structure, just "how far from average."
    """
    numeric_cols = [
        c for c, dt in column_dtypes.items() if dt in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT)
    ]
    if len(numeric_cols) < 1 or len(df) < 10:
        return None

    X = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)

    std = X.std(ddof=0).replace(0, 1)
    Z = (X - X.mean()) / std
    distances = np.sqrt((Z ** 2).sum(axis=1))

    threshold = np.percentile(distances, config.DISTANCE_BASELINE_PERCENTILE)
    flagged_mask = distances > threshold
    flagged_indices = [int(i) for i in df.index[flagged_mask][:1000]]

    return {
        "method": "euclidean_distance_from_centroid_zscore",
        "threshold": round(float(threshold), 4),
        "flagged_row_indices": flagged_indices,
    }


def compute_agreement(if_result: dict, baseline_result: dict) -> float:
    if not if_result or not baseline_result:
        return None
    a = set(if_result["flagged_row_indices"])
    b = set(baseline_result["flagged_row_indices"])
    union = a | b
    if not union:
        return 1.0
    return round(len(a & b) / len(union), 4)
