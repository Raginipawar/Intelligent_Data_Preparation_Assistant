"""
reasoning_generator.py — Dynamic, dataset-backed natural language explanations for algorithm recommendations.
"""
from __future__ import annotations

from typing import List
from app.meta_features import MetaFeatures
from app.recommend_schemas import TaskType


def generate_reasoning(algorithm: str, score: float, mf: MetaFeatures) -> List[str]:
    """Generates plain-language reasoning tied directly to actual observed dataset characteristics."""
    reasons = []

    # Dataset size reasoning
    if mf.n_rows < 300:
        if "Forest" in algorithm or "Ridge" in algorithm or "Logistic" in algorithm:
            reasons.append(
                f"Small sample size ({mf.n_rows:,} rows) favors models with stronger inductive bias to prevent overfitting."
            )
        elif "Boosting" in algorithm:
            reasons.append(
                f"Dataset is relatively small ({mf.n_rows:,} rows); boosting iterations should be kept low to avoid overfitting."
            )
    elif mf.n_rows > 10000:
        if "HistGradientBoosting" in algorithm:
            reasons.append(
                f"Large dataset size ({mf.n_rows:,} rows) heavily favors histogram-based gradient boosting for fast parallel training."
            )
        elif "SVC" in algorithm or "KNeighbors" in algorithm:
            reasons.append(
                f"Large row count ({mf.n_rows:,} rows) increases computational complexity for distance-based kernel methods."
            )
        else:
            reasons.append(
                f"Dataset contains {mf.n_rows:,} rows, providing sufficient training volume for ensemble models."
            )
    else:
        reasons.append(
            f"Dataset size ({mf.n_rows:,} rows) provides a balanced volume suitable for standard cross-validated estimators."
        )

    # Feature composition & dimensionality
    if mf.n_categorical > 0 or mf.n_boolean > 0:
        if "Forest" in algorithm or "Boosting" in algorithm or "Trees" in algorithm:
            reasons.append(
                f"Contains {mf.n_categorical} categorical and {mf.n_boolean} boolean features; tree-based models split natively across mixed feature types."
            )
        elif "Logistic" in algorithm or "Ridge" in algorithm or "SVC" in algorithm:
            reasons.append(
                f"Contains categorical/boolean features; linear models require proper one-hot or target encoding."
            )

    if mf.feature_to_sample_ratio > 0.1:
        if "ExtraTrees" in algorithm or "Logistic" in algorithm or "Ridge" in algorithm or "SVC" in algorithm:
            reasons.append(
                f"Moderate to high feature-to-sample ratio ({mf.feature_to_sample_ratio}); regularized or randomized feature subspace methods help prevent variance explosion."
            )
        elif "KNeighbors" in algorithm:
            reasons.append(
                f"Feature dimensionality relative to samples ({mf.feature_to_sample_ratio}) may degrade distance metrics (curse of dimensionality)."
            )

    # Class imbalance
    if mf.task_type in [TaskType.BINARY_CLASSIFICATION, TaskType.MULTICLASS_CLASSIFICATION]:
        if mf.class_imbalance_ratio > 3.0:
            if "Forest" in algorithm or "Boosting" in algorithm or "Trees" in algorithm:
                reasons.append(
                    f"Noticed significant class imbalance (ratio {mf.class_imbalance_ratio}:1); tree ensembles allow class weighting and handle thresholding effectively."
                )

    # Multicollinearity
    if mf.mean_absolute_correlation > 0.6:
        if "Forest" in algorithm or "Trees" in algorithm or "Boosting" in algorithm:
            reasons.append(
                f"High feature correlation detected (mean |r| = {mf.mean_absolute_correlation}); tree ensembles naturally handle redundant features without collinearity failure."
            )
        elif "Logistic" in algorithm:
            reasons.append(
                f"High feature correlation detected (mean |r| = {mf.mean_absolute_correlation}); coefficient estimates may exhibit high variance."
            )

    # Skewness
    if mf.high_skew_count > 0 and ("Forest" in algorithm or "Boosting" in algorithm or "Trees" in algorithm):
        reasons.append(
            f"{mf.high_skew_count} numerical features are heavily skewed; non-parametric tree splits are invariant to monotonic transformations."
        )

    # Target specific summary
    if mf.target_column:
        reasons.append(
            f"Evaluated against target column '{mf.target_column}' for task '{mf.task_type.value}'."
        )

    return reasons
