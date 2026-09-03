"""
target_detection.py — heuristic scoring to guess which column is the
prediction target. No ground truth exists for this, so we score every
column on several weak signals and report the full ranking transparently
(never just a silent guess) so downstream humans/modules can override it.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from app.schemas import InferredDType

NAME_KEYWORDS = (
    "target", "label", "class", "outcome", "result", "response",
    "churn", "churned", "y", "default", "fraud", "diagnosis", "survived",
)

MISSINGNESS_PENALTY_WEIGHT = 0.5
NAME_MATCH_BONUS = 3.0
POSITION_BONUS = 1.0        # last column gets a boost (common convention)
LOW_CARDINALITY_BONUS = 2.0
HIGH_CARDINALITY_PENALTY = 3.0


def _score_column(name: str, series: pd.Series, dtype: InferredDType, position_ratio: float, n_rows: int) -> Dict:
    reasons: List[str] = []
    score = 0.0

    lowered = name.lower()
    if any(kw in lowered for kw in NAME_KEYWORDS):
        score += NAME_MATCH_BONUS
        reasons.append(f"column name '{name}' matches a common target keyword")

    if position_ratio >= 0.9:
        score += POSITION_BONUS
        reasons.append("appears near the end of the dataset (common target convention)")

    n_unique = series.nunique(dropna=True)
    unique_ratio = n_unique / max(n_rows, 1)

    if dtype in (InferredDType.BOOLEAN, InferredDType.CATEGORICAL) and 2 <= n_unique <= 20:
        score += LOW_CARDINALITY_BONUS
        reasons.append(f"low-cardinality {dtype.value} column ({n_unique} classes) — looks like a classification label")
    elif dtype in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT) and unique_ratio < 0.5:
        score += LOW_CARDINALITY_BONUS * 0.5
        reasons.append("numeric column with repeated values — plausible regression target")

    if dtype == InferredDType.TEXT_FREEFORM or unique_ratio > 0.9:
        score -= HIGH_CARDINALITY_PENALTY
        reasons.append("high-cardinality / free-text — looks like an identifier, not a target")

    missing_pct = series.isna().mean()
    score -= MISSINGNESS_PENALTY_WEIGHT * missing_pct * 10
    if missing_pct > 0.3:
        reasons.append(f"{missing_pct:.0%} missing — weak candidate")

    if any(tok in lowered for tok in ("id", "index", "uuid", "guid")):
        score -= HIGH_CARDINALITY_PENALTY
        reasons.append("name suggests an identifier column")

    return {"score": round(score, 3), "reasoning": "; ".join(reasons) if reasons else "no strong signal either way"}


def detect_target(df: pd.DataFrame, column_dtypes: Dict[str, InferredDType]) -> dict:
    n_rows = len(df)
    n_cols = max(len(df.columns), 1)
    candidates = []

    for i, col in enumerate(df.columns):
        dtype = column_dtypes.get(col, InferredDType.UNKNOWN)
        position_ratio = (i + 1) / n_cols
        scored = _score_column(col, df[col], dtype, position_ratio, n_rows)
        candidates.append({"column": col, "score": scored["score"], "reasoning": scored["reasoning"]})

    candidates.sort(key=lambda c: c["score"], reverse=True)

    if not candidates or candidates[0]["score"] <= 0:
        return {
            "suggested_target": None,
            "confidence": 0.0,
            "reasoning": "No column scored positively on target-likelihood heuristics.",
            "task_type_guess": None,
            "candidates": candidates[:10],
        }

    top = candidates[0]
    runner_up_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
    gap = top["score"] - runner_up_score
    # Confidence: squashed gap, bounded [0, 1] — a big lead over the runner-up means high confidence.
    confidence = round(min(1.0, max(0.1, gap / (abs(top["score"]) + 1e-6))), 3)

    top_dtype = column_dtypes.get(top["column"], InferredDType.UNKNOWN)
    if top_dtype in (InferredDType.BOOLEAN, InferredDType.CATEGORICAL):
        task_type = "classification"
    elif top_dtype in (InferredDType.NUMERIC_INT, InferredDType.NUMERIC_FLOAT):
        task_type = "regression" if df[top["column"]].nunique() > 20 else "classification"
    else:
        task_type = None

    return {
        "suggested_target": top["column"],
        "confidence": confidence,
        "reasoning": top["reasoning"],
        "task_type_guess": task_type,
        "candidates": candidates[:10],
    }
