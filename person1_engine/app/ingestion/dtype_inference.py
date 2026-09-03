"""
dtype_inference.py — classifies every column into one of:
numeric_int, numeric_float, categorical, datetime, boolean, text_freeform

Pandas' own dtype (int64/float64/object/...) is a starting point but is not
enough: an "object" column might be free text, a low-cardinality category,
a badly-parsed date, or a boolean spelled as "Yes"/"No". We re-derive intent
from the actual values.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from app.schemas import InferredDType

BOOLEAN_TRUE_TOKENS = {"true", "yes", "y", "1", "t"}
BOOLEAN_FALSE_TOKENS = {"false", "no", "n", "0", "f"}

CATEGORICAL_UNIQUE_RATIO_CEILING = 0.2   # object columns below this ratio look categorical
CATEGORICAL_MAX_UNIQUE = 50              # ...unless they have a LOT of distinct values anyway
DATETIME_PARSE_SUCCESS_THRESHOLD = 0.9   # 90%+ of non-null values parse as dates -> call it datetime
TEXT_AVG_LEN_THRESHOLD = 25              # long average string length suggests free text


def _looks_boolean(series: pd.Series) -> bool:
    non_null = series.dropna().astype(str).str.strip().str.lower()
    if non_null.empty:
        return False
    uniques = set(non_null.unique())
    if uniques <= (BOOLEAN_TRUE_TOKENS | BOOLEAN_FALSE_TOKENS) and len(uniques) <= 2:
        return True
    return False


def _looks_datetime(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    sample = non_null.sample(min(len(non_null), 200), random_state=0)
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    success_rate = parsed.notna().mean()
    return success_rate >= DATETIME_PARSE_SUCCESS_THRESHOLD


def _has_mixed_types(series: pd.Series) -> bool:
    """Flags object columns where some values look numeric and others don't —
    a classic 'looked fine in Excel, breaks in pandas' symptom. Deliberately
    sensitive to even a handful of stray non-numeric values (e.g. a couple of
    blank-space placeholders in an otherwise-numeric column), since that's the
    more common real-world messy-data pattern than a clean 50/50 split."""
    non_null = series.dropna()
    if non_null.empty or series.dtype != object:
        return False
    non_null = non_null.astype(str).str.strip()
    numeric_like = pd.to_numeric(non_null, errors="coerce").notna()
    n_numeric = int(numeric_like.sum())
    n_non_numeric = int((~numeric_like).sum())
    return n_numeric > 0 and n_non_numeric > 0  # at least one of each -> genuinely mixed


def infer_column(series: pd.Series) -> Tuple[InferredDType, bool]:
    """Returns (inferred_dtype, mixed_type_flag)."""
    non_null = series.dropna()
    if non_null.empty:
        return InferredDType.UNKNOWN, False

    mixed_flag = _has_mixed_types(series)

    if pd.api.types.is_bool_dtype(series):
        return InferredDType.BOOLEAN, False

    if pd.api.types.is_numeric_dtype(series):
        is_int_like = np.all(np.equal(np.mod(non_null, 1), 0))
        n_unique = non_null.nunique()
        if is_int_like and n_unique <= 2 and set(non_null.unique()) <= {0, 1}:
            return InferredDType.BOOLEAN, mixed_flag
        return (InferredDType.NUMERIC_INT if is_int_like else InferredDType.NUMERIC_FLOAT), mixed_flag

    if pd.api.types.is_datetime64_any_dtype(series):
        return InferredDType.DATETIME, mixed_flag

    # Remaining case: object / string-like column. Check in order of specificity.
    if _looks_boolean(series):
        return InferredDType.BOOLEAN, mixed_flag

    if _looks_datetime(series):
        return InferredDType.DATETIME, mixed_flag

    numeric_coerced = pd.to_numeric(non_null, errors="coerce")
    if numeric_coerced.notna().mean() >= 0.95:
        is_int_like = np.all(np.equal(np.mod(numeric_coerced.dropna(), 1), 0))
        return (InferredDType.NUMERIC_INT if is_int_like else InferredDType.NUMERIC_FLOAT), mixed_flag

    n_unique = non_null.nunique()
    unique_ratio = n_unique / max(len(non_null), 1)
    avg_len = non_null.astype(str).str.len().mean()

    if unique_ratio <= CATEGORICAL_UNIQUE_RATIO_CEILING or n_unique <= CATEGORICAL_MAX_UNIQUE:
        if avg_len <= TEXT_AVG_LEN_THRESHOLD:
            return InferredDType.CATEGORICAL, mixed_flag

    return InferredDType.TEXT_FREEFORM, mixed_flag


def infer_all_dtypes(df: pd.DataFrame) -> List[dict]:
    results = []
    for col in df.columns:
        dtype, mixed = infer_column(df[col])
        sample_values = df[col].dropna().head(5).tolist()
        # Make sure sample values are JSON-serialisable.
        sample_values = [v.item() if hasattr(v, "item") else v for v in sample_values]
        sample_values = [str(v) if isinstance(v, (pd.Timestamp,)) else v for v in sample_values]
        results.append(
            {
                "name": col,
                "inferred_dtype": dtype,
                "pandas_dtype": str(df[col].dtype),
                "sample_values": sample_values,
                "mixed_type_flag": mixed,
            }
        )
    return results
