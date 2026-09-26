"""
meta_features.py — Extract statistical, dimensional, and domain meta-features from a pandas DataFrame.
"""
from __future__ import annotations

from typing import Optional, Tuple
import numpy as np
import pandas as pd

from app.recommend_schemas import MetaFeatures, TaskType


def infer_target_column(df: pd.DataFrame) -> Optional[str]:
    """Heuristic to infer target column if not provided."""
    target_names = ["target", "label", "class", "churn", "survived", "y", "output", "price", "sale_price"]
    for col in df.columns:
        if str(col).lower() in target_names:
            return str(col)

    # Check last column
    if len(df.columns) > 0:
        return str(df.columns[-1])
    return None


def detect_task_type(series: pd.Series) -> Tuple[TaskType, int, float]:
    """
    Detects whether task is binary classification, multiclass classification, or regression.
    Returns (task_type, target_cardinality, class_imbalance_ratio).
    """
    clean_s = series.dropna()
    if len(clean_s) == 0:
        return TaskType.UNKNOWN, 0, 1.0

    n_unique = clean_s.nunique()

    # Numeric floating or continuous with high uniqueness -> Regression
    if pd.api.types.is_numeric_dtype(clean_s) and not pd.api.types.is_bool_dtype(clean_s):
        if n_unique > 20 or (n_unique > 10 and not pd.api.types.is_integer_dtype(clean_s)):
            return TaskType.REGRESSION, n_unique, 1.0

    # Categorical, boolean, or low-cardinality integer
    if n_unique == 2:
        vc = clean_s.value_counts()
        imbalance = float(vc.max() / max(vc.min(), 1))
        return TaskType.BINARY_CLASSIFICATION, 2, imbalance
    elif n_unique <= 20:
        vc = clean_s.value_counts()
        imbalance = float(vc.max() / max(vc.min(), 1))
        return TaskType.MULTICLASS_CLASSIFICATION, n_unique, imbalance
    else:
        return TaskType.REGRESSION, n_unique, 1.0


def extract_meta_features(
    df: pd.DataFrame,
    target_col: Optional[str] = None
) -> MetaFeatures:
    """Extracts meta-features from the DataFrame."""
    n_rows, n_cols = df.shape
    if n_rows == 0 or n_cols == 0:
        return MetaFeatures(n_rows=n_rows, n_columns=n_cols)

    if not target_col or target_col not in df.columns:
        target_col = infer_target_column(df)

    if target_col and target_col in df.columns:
        target_series = df[target_col]
        task_type, target_cardinality, imbalance_ratio = detect_task_type(target_series)
        feature_df = df.drop(columns=[target_col])
    else:
        task_type = TaskType.UNKNOWN
        target_cardinality = 0
        imbalance_ratio = 1.0
        feature_df = df

    n_features = feature_df.shape[1]
    feature_to_sample_ratio = round(n_features / max(n_rows, 1), 4)

    # Feature dtypes
    n_numerical = 0
    n_categorical = 0
    n_boolean = 0
    n_text = 0
    n_datetime = 0
    high_skew_count = 0

    numeric_cols = []

    for col in feature_df.columns:
        s = feature_df[col]
        if pd.api.types.is_bool_dtype(s):
            n_boolean += 1
        elif pd.api.types.is_datetime64_any_dtype(s):
            n_datetime += 1
        elif pd.api.types.is_numeric_dtype(s):
            n_numerical += 1
            numeric_cols.append(col)
            # Check skewness
            clean_s = s.dropna()
            if len(clean_s) > 10:
                skew = abs(clean_s.skew())
                if skew > 1.5:
                    high_skew_count += 1
        else:
            # Check if object / string
            clean_s = s.dropna().astype(str)
            avg_len = clean_s.str.len().mean() if len(clean_s) > 0 else 0
            if avg_len > 30 and s.nunique() > 20:
                n_text += 1
            else:
                n_categorical += 1

    # Missing cell percentage
    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    missing_cell_pct = round(float(missing_cells / max(total_cells, 1)) * 100, 2)

    # Multicollinearity (mean absolute correlation)
    mean_abs_corr = 0.0
    if len(numeric_cols) >= 2:
        try:
            corr_matrix = feature_df[numeric_cols].corr().abs()
            # Extract upper triangle excluding diagonal
            upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            values = upper_tri.stack().values
            if len(values) > 0:
                computed = float(np.mean(values))
                # A constant numeric column has undefined (NaN) correlation with everything;
                # np.mean over a NaN-containing array is itself NaN, and doesn't raise — so it
                # slips past the except below and reaches FastAPI's JSON renderer, which
                # rejects NaN outright (Starlette's default JSONResponse uses allow_nan=False).
                # Fall back to the documented 0.0 default (see recommend_schemas.py) instead.
                if not np.isnan(computed):
                    mean_abs_corr = round(computed, 4)
        except Exception:
            mean_abs_corr = 0.0

    return MetaFeatures(
        n_rows=n_rows,
        n_columns=n_cols,
        n_features=n_features,
        feature_to_sample_ratio=feature_to_sample_ratio,
        task_type=task_type,
        target_column=target_col,
        target_cardinality=target_cardinality,
        n_numerical=n_numerical,
        n_categorical=n_categorical,
        n_boolean=n_boolean,
        n_text=n_text,
        n_datetime=n_datetime,
        class_imbalance_ratio=round(imbalance_ratio, 2),
        missing_cell_pct=missing_cell_pct,
        high_skew_count=high_skew_count,
        mean_absolute_correlation=mean_abs_corr,
    )
