"""
recommend_engine.py — Scopes, scores, and ranks candidate ML algorithms using dataset meta-features.
"""
from __future__ import annotations

from typing import List
from app.meta_features import MetaFeatures
from app.recommend_schemas import AlgorithmRecommendation, TaskType
from app.reasoning_generator import generate_reasoning


def score_classification_candidates(mf: MetaFeatures) -> List[dict]:
    """Scores candidate classification models based on meta-features."""
    candidates = [
        {
            "algorithm": "RandomForestClassifier",
            "model_class": "sklearn.ensemble.RandomForestClassifier",
            "base_score": 0.85,
        },
        {
            "algorithm": "GradientBoostingClassifier",
            "model_class": "sklearn.ensemble.GradientBoostingClassifier",
            "base_score": 0.88,
        },
        {
            "algorithm": "HistGradientBoostingClassifier",
            "model_class": "sklearn.ensemble.HistGradientBoostingClassifier",
            "base_score": 0.87,
        },
        {
            "algorithm": "ExtraTreesClassifier",
            "model_class": "sklearn.ensemble.ExtraTreesClassifier",
            "base_score": 0.83,
        },
        {
            "algorithm": "LogisticRegression",
            "model_class": "sklearn.linear_model.LogisticRegression",
            "base_score": 0.75,
        },
        {
            "algorithm": "SVC",
            "model_class": "sklearn.svm.SVC",
            "base_score": 0.70,
        },
        {
            "algorithm": "KNeighborsClassifier",
            "model_class": "sklearn.neighbors.KNeighborsClassifier",
            "base_score": 0.65,
        },
    ]

    scored = []
    for item in candidates:
        score = item["base_score"]
        algo = item["algorithm"]

        # Adjustments based on dataset size
        if mf.n_rows < 300:
            if algo in ["LogisticRegression", "RandomForestClassifier", "KNeighborsClassifier"]:
                score += 0.08
            elif algo in ["HistGradientBoostingClassifier", "GradientBoostingClassifier"]:
                score -= 0.10
        elif mf.n_rows > 10000:
            if algo == "HistGradientBoostingClassifier":
                score += 0.12
            elif algo == "GradientBoostingClassifier":
                score += 0.05
            elif algo in ["SVC", "KNeighborsClassifier"]:
                score -= 0.25  # O(N^2) or slow inference

        # Adjustments based on dimensionality (D/N ratio)
        if mf.feature_to_sample_ratio > 0.1:
            if algo in ["LogisticRegression", "ExtraTreesClassifier", "SVC"]:
                score += 0.07
            elif algo == "KNeighborsClassifier":
                score -= 0.15  # Curse of dimensionality

        # Class imbalance adjustment
        if mf.class_imbalance_ratio > 3.0:
            if algo in ["RandomForestClassifier", "ExtraTreesClassifier", "GradientBoostingClassifier", "HistGradientBoostingClassifier"]:
                score += 0.06
            elif algo == "KNeighborsClassifier":
                score -= 0.08

        # Categorical feature presence
        if mf.n_categorical > 0 or mf.n_boolean > 0:
            if algo in ["RandomForestClassifier", "HistGradientBoostingClassifier", "GradientBoostingClassifier", "ExtraTreesClassifier"]:
                score += 0.05

        # Multicollinearity
        if mf.mean_absolute_correlation > 0.6:
            if algo in ["RandomForestClassifier", "ExtraTreesClassifier", "HistGradientBoostingClassifier"]:
                score += 0.05
            elif algo == "LogisticRegression":
                score -= 0.05

        scored.append({
            "algorithm": algo,
            "model_class": item["model_class"],
            "score": round(max(0.1, min(0.99, score)), 3),
        })

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def score_regression_candidates(mf: MetaFeatures) -> List[dict]:
    """Scores candidate regression models based on meta-features."""
    candidates = [
        {
            "algorithm": "RandomForestRegressor",
            "model_class": "sklearn.ensemble.RandomForestRegressor",
            "base_score": 0.85,
        },
        {
            "algorithm": "GradientBoostingRegressor",
            "model_class": "sklearn.ensemble.GradientBoostingRegressor",
            "base_score": 0.88,
        },
        {
            "algorithm": "HistGradientBoostingRegressor",
            "model_class": "sklearn.ensemble.HistGradientBoostingRegressor",
            "base_score": 0.87,
        },
        {
            "algorithm": "ExtraTreesRegressor",
            "model_class": "sklearn.ensemble.ExtraTreesRegressor",
            "base_score": 0.82,
        },
        {
            "algorithm": "Ridge",
            "model_class": "sklearn.linear_model.Ridge",
            "base_score": 0.74,
        },
        {
            "algorithm": "SVR",
            "model_class": "sklearn.svm.SVR",
            "base_score": 0.68,
        },
        {
            "algorithm": "KNeighborsRegressor",
            "model_class": "sklearn.neighbors.KNeighborsRegressor",
            "base_score": 0.64,
        },
    ]

    scored = []
    for item in candidates:
        score = item["base_score"]
        algo = item["algorithm"]

        if mf.n_rows < 300:
            if algo in ["Ridge", "RandomForestRegressor", "KNeighborsRegressor"]:
                score += 0.08
            elif algo in ["HistGradientBoostingRegressor", "GradientBoostingRegressor"]:
                score -= 0.10
        elif mf.n_rows > 10000:
            if algo == "HistGradientBoostingRegressor":
                score += 0.12
            elif algo in ["SVR", "KNeighborsRegressor"]:
                score -= 0.25

        if mf.feature_to_sample_ratio > 0.1:
            if algo in ["Ridge", "ExtraTreesRegressor"]:
                score += 0.08

        if mf.high_skew_count > 0:
            if algo in ["RandomForestRegressor", "HistGradientBoostingRegressor", "ExtraTreesRegressor"]:
                score += 0.06

        scored.append({
            "algorithm": algo,
            "model_class": item["model_class"],
            "score": round(max(0.1, min(0.99, score)), 3),
        })

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def rank_recommendations(mf: MetaFeatures) -> List[AlgorithmRecommendation]:
    """Generates ranked AlgorithmRecommendation objects with data-backed reasoning."""
    if mf.task_type in [TaskType.BINARY_CLASSIFICATION, TaskType.MULTICLASS_CLASSIFICATION]:
        scored_candidates = score_classification_candidates(mf)
    elif mf.task_type == TaskType.REGRESSION:
        scored_candidates = score_regression_candidates(mf)
    else:
        # Fallback to classification
        scored_candidates = score_classification_candidates(mf)

    recommendations = []
    for idx, item in enumerate(scored_candidates, 1):
        score = item["score"]
        suitability = "high" if score >= 0.82 else ("medium" if score >= 0.70 else "low")
        reasoning = generate_reasoning(item["algorithm"], score, mf)

        rec = AlgorithmRecommendation(
            algorithm=item["algorithm"],
            model_class=item["model_class"],
            rank=idx,
            recommendation_score=score,
            reasoning=reasoning,
            suitability=suitability,
        )
        recommendations.append(rec)

    return recommendations
