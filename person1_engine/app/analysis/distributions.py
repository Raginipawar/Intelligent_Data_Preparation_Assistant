from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from app.schemas import InferredDType


def analyze_distributions(df: pd.DataFrame, column_dtypes: dict, n_bins: int = 20) -> dict:
    """column_dtypes: {col_name: InferredDType} from dtype_inference, so we only
    run numeric stats on columns we've actually classified as numeric —
    not just whatever pandas' raw dtype happens to say."""
    columns = {}
    numeric_cols = [
        c for c, dt in column_dtypes.items() if dt in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT)
    ]

    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        counts, bin_edges = np.histogram(series, bins=n_bins)
        columns[col] = {
            "count": int(series.count()),
            "mean": round(float(series.mean()), 6),
            "std": round(float(series.std(ddof=1)) if series.count() > 1 else 0.0, 6),
            "min": round(float(series.min()), 6),
            "max": round(float(series.max()), 6),
            "median": round(float(series.median()), 6),
            "skewness": round(float(stats.skew(series)), 6) if series.count() > 2 else None,
            "kurtosis": round(float(stats.kurtosis(series)), 6) if series.count() > 3 else None,
            "histogram": {
                "bin_edges": [round(float(b), 6) for b in bin_edges],
                "counts": [int(c) for c in counts],
            },
        }

    return {"columns": columns}
