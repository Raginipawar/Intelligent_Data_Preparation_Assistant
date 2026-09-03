"""
lightgbm_signal.py — the "Quick Signal Layer": a fast, low-effort LightGBM
fit purely to surface rough feature importance for Person 2's head start.
This is NOT meant to be a good model — no tuning, no CV, no leakage
guarding beyond the basics. If it fails for any reason, the report should
say so and move on rather than blocking the rest of the pipeline.
"""
from __future__ import annotations

from typing import Dict, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from app.schemas import InferredDType

MIN_ROWS_FOR_SURROGATE = 30
MAX_TARGET_MISSING_PCT = 0.3


def _prepare_features(df: pd.DataFrame, target_col: str, column_dtypes: Dict[str, InferredDType]):
    feature_cols = [c for c in df.columns if c != target_col]
    X = df[feature_cols].copy()

    for col in feature_cols:
        dtype = column_dtypes.get(col, InferredDType.UNKNOWN)
        if dtype == InferredDType.CATEGORICAL or dtype == InferredDType.BOOLEAN:
            X[col] = X[col].astype("category")
        elif dtype == InferredDType.DATETIME:
            # Cheap signal from a datetime column without full feature engineering
            # (that's Person 2's job) — just expose something numeric.
            parsed = pd.to_datetime(X[col], errors="coerce", format="mixed")
            X[col] = parsed.astype("int64") // 10**9
            X[col] = X[col].replace(-9223372036, np.nan)
        elif dtype == InferredDType.TEXT_FREEFORM:
            X = X.drop(columns=[col])  # raw free text isn't fair game for a rough surrogate
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce")

    return X


def run_surrogate_signal(
    df: pd.DataFrame,
    column_dtypes: Dict[str, InferredDType],
    target_col: Optional[str],
    task_type: Optional[str],
) -> dict:
    if not target_col or target_col not in df.columns:
        return {"ran": False, "note": "Skipped: no target column detected with sufficient confidence."}

    if len(df) < MIN_ROWS_FOR_SURROGATE:
        return {"ran": False, "note": f"Skipped: fewer than {MIN_ROWS_FOR_SURROGATE} rows available."}

    y_raw = df[target_col]
    if y_raw.isna().mean() > MAX_TARGET_MISSING_PCT:
        return {"ran": False, "note": "Skipped: target column has too much missing data."}

    valid_rows = y_raw.notna()
    df_valid = df.loc[valid_rows]
    y_raw = y_raw.loc[valid_rows]

    try:
        X = _prepare_features(df_valid, target_col, column_dtypes)
        if X.shape[1] == 0:
            return {"ran": False, "note": "Skipped: no usable feature columns remained after filtering."}

        if task_type == "classification" or column_dtypes.get(target_col) in (
            InferredDType.CATEGORICAL,
            InferredDType.BOOLEAN,
        ):
            le = LabelEncoder()
            y = le.fit_transform(y_raw.astype(str))
            objective = "multiclass" if len(le.classes_) > 2 else "binary"
            params = {"objective": objective, "verbosity": -1}
            if objective == "multiclass":
                params["num_class"] = len(le.classes_)
            resolved_task_type = "classification"
        else:
            y = pd.to_numeric(y_raw, errors="coerce")
            keep = y.notna()
            X, y = X.loc[keep], y.loc[keep]
            params = {"objective": "regression", "verbosity": -1}
            resolved_task_type = "regression"

        train_set = lgb.Dataset(X, label=y, free_raw_data=False)
        booster = lgb.train(params, train_set, num_boost_round=50)

        importances = booster.feature_importance(importance_type="gain")
        total = importances.sum() or 1.0
        importance_map = {
            col: round(float(imp) / float(total), 6)
            for col, imp in sorted(zip(X.columns, importances), key=lambda p: p[1], reverse=True)
        }

        return {
            "ran": True,
            "target_used": target_col,
            "task_type": resolved_task_type,
            "importances": importance_map,
            "note": "Rough signal only — trained on raw/lightly-typed features with no tuning. "
                    "Not a substitute for Person 2's preprocessing-aware model.",
        }
    except Exception as exc:  # noqa: BLE001 — this layer must never break the whole report
        return {"ran": False, "note": f"Surrogate model failed: {exc}"}
