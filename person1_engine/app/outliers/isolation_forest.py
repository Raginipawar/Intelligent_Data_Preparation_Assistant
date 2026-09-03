from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app import config
from app.schemas import InferredDType


def run_isolation_forest(df: pd.DataFrame, column_dtypes: Dict[str, InferredDType]) -> dict:
    numeric_cols = [
        c for c, dt in column_dtypes.items() if dt in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT)
    ]
    if len(numeric_cols) < 1 or len(df) < 10:
        return None  # not enough signal to run meaningfully

    X = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    # Isolation Forest can't handle NaNs — impute with column median for THIS
    # detection pass only (this does not mutate the caller's dataframe).
    X = X.fillna(X.median(numeric_only=True))
    X = X.fillna(0.0)  # any all-NaN column falls back to 0

    contamination = config.ISOLATION_FOREST_CONTAMINATION
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    model.fit(X)
    predictions = model.predict(X)  # -1 = anomaly, 1 = normal
    flagged_mask = predictions == -1
    flagged_indices = [int(i) for i in df.index[flagged_mask][:1000]]

    # Column-level involvement: for flagged rows, which columns look most
    # unusual (|z-score| > 2)? A lightweight stand-in for full SHAP attribution.
    z_scores = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
    involvement: Dict[str, int] = {c: 0 for c in numeric_cols}
    if flagged_mask.any():
        flagged_z = z_scores.loc[flagged_mask]
        contributing = (flagged_z.abs() > 2)
        for c in numeric_cols:
            involvement[c] = int(contributing[c].sum())

    return {
        "contamination": contamination,
        "dataset_anomaly_rate": round(float(flagged_mask.mean()), 4),
        "flagged_row_indices": flagged_indices,
        "column_involvement": involvement,
    }
