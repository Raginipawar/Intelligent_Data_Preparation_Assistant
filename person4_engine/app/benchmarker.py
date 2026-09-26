"""
benchmarker.py — Safe, fast empirical cross-validation benchmarking for top candidate algorithms.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold, KFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC, SVR

from app.meta_features import MetaFeatures
from app.recommend_schemas import AlgorithmRecommendation, BenchmarkResult, TaskType


MODEL_MAPPING = {
    "RandomForestClassifier": RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1),
    "GradientBoostingClassifier": GradientBoostingClassifier(n_estimators=50, random_state=42),
    "HistGradientBoostingClassifier": HistGradientBoostingClassifier(max_iter=50, random_state=42),
    "ExtraTreesClassifier": ExtraTreesClassifier(n_estimators=50, random_state=42, n_jobs=-1),
    "LogisticRegression": LogisticRegression(max_iter=200, random_state=42),
    "SVC": SVC(probability=True, random_state=42),
    "KNeighborsClassifier": KNeighborsClassifier(),

    "RandomForestRegressor": RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1),
    "GradientBoostingRegressor": GradientBoostingRegressor(n_estimators=50, random_state=42),
    "HistGradientBoostingRegressor": HistGradientBoostingRegressor(max_iter=50, random_state=42),
    "ExtraTreesRegressor": ExtraTreesRegressor(n_estimators=50, random_state=42, n_jobs=-1),
    "Ridge": Ridge(random_state=42),
    "SVR": SVR(),
    "KNeighborsRegressor": KNeighborsRegressor(),
}


def build_preprocessing_pipeline(X: pd.DataFrame) -> ColumnTransformer:
    """Builds a basic, leak-free preprocessing pipeline for empirical benchmarking."""
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

    num_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    cat_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_transformer, num_cols),
            ("cat", cat_transformer, cat_cols)
        ],
        remainder="drop"
    )
    return preprocessor


def benchmark_candidate(
    algorithm_name: str,
    df: pd.DataFrame,
    target_col: str,
    task_type: TaskType,
    cv_folds: int = 5
) -> BenchmarkResult:
    """Runs cross-validation benchmark on a single algorithm."""
    start_time = time.time()
    model = MODEL_MAPPING.get(algorithm_name)
    if model is None:
        return BenchmarkResult(
            metric="none",
            score=0.0,
            status="skipped",
            note=f"Estimator {algorithm_name} not available for benchmarking."
        )

    if target_col not in df.columns:
        return BenchmarkResult(
            metric="none",
            score=0.0,
            status="skipped",
            note=f"Target column '{target_col}' missing from dataset."
        )

    clean_df = df.dropna(subset=[target_col]).copy()
    if len(clean_df) < 10:
        return BenchmarkResult(
            metric="none",
            score=0.0,
            status="skipped",
            note="Dataset has fewer than 10 valid rows for benchmarking."
        )

    X = clean_df.drop(columns=[target_col])
    y = clean_df[target_col]

    # pandas' select_dtypes(exclude=[np.number]) does NOT exclude bool columns
    # (bool isn't a subtype of np.number in pandas' eyes), so a real boolean
    # column falls into build_preprocessing_pipeline's categorical bucket and
    # hits SimpleImputer(strategy="most_frequent") — which scikit-learn
    # explicitly refuses on raw bool arrays ("SimpleImputer does not support
    # data with dtype bool"). Cast to int64 first so it's treated as the plain
    # 0/1 numeric feature it actually is; this silently broke benchmarking for
    # every dataset with a boolean column (Person 1 and Person 3 both produce
    # real boolean dtype columns), not just this one.
    bool_cols = X.select_dtypes(include="bool").columns
    if len(bool_cols) > 0:
        X = X.copy()
        X[bool_cols] = X[bool_cols].astype("int64")

    try:
        preprocessor = build_preprocessing_pipeline(X)
        full_pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("estimator", model)
        ])

        if task_type in [TaskType.BINARY_CLASSIFICATION, TaskType.MULTICLASS_CLASSIFICATION]:
            # Metric choice
            n_unique = y.nunique()
            if n_unique < 2:
                return BenchmarkResult(metric="accuracy", score=1.0, status="skipped", note="Target has only 1 class.")

            metric = "f1_macro" if task_type == TaskType.MULTICLASS_CLASSIFICATION or (y.value_counts().max() / max(y.value_counts().min(), 1)) > 3.0 else "accuracy"
            cv = StratifiedKFold(n_splits=min(cv_folds, y.value_counts().min()), shuffle=True, random_state=42)
        else:
            metric = "r2"
            cv = KFold(n_splits=min(cv_folds, len(y)), shuffle=True, random_state=42)

        scores = cross_val_score(full_pipeline, X, y, cv=cv, scoring=metric, error_score="raise")
        elapsed = round(time.time() - start_time, 3)

        mean_score = float(np.mean(scores))
        rounded_scores = [round(float(s), 4) for s in scores]

        return BenchmarkResult(
            metric=metric,
            score=round(mean_score, 4),
            cv_scores=rounded_scores,
            fit_time_seconds=elapsed,
            status="completed"
        )
    except Exception as e:
        return BenchmarkResult(
            metric="none",
            score=0.0,
            fit_time_seconds=round(time.time() - start_time, 3),
            status="failed",
            note=f"Benchmarking error: {str(e)}"
        )


def benchmark_top_recommendations(
    recommendations: List[AlgorithmRecommendation],
    df: pd.DataFrame,
    mf: MetaFeatures,
    top_k: int = 3
) -> List[AlgorithmRecommendation]:
    """Runs empirical benchmark on top_k recommended algorithms."""
    if not mf.target_column or mf.target_column not in df.columns:
        return recommendations

    for i in range(min(top_k, len(recommendations))):
        rec = recommendations[i]
        res = benchmark_candidate(
            algorithm_name=rec.algorithm,
            df=df,
            target_col=mf.target_column,
            task_type=mf.task_type,
        )
        rec.benchmark = res

    return recommendations
