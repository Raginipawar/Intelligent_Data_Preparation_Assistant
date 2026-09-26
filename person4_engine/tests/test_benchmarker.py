"""
test_benchmarker.py — Tests cross-validation empirical benchmarker.
"""
import numpy as np
import pandas as pd
from app.benchmarker import benchmark_candidate
from app.recommend_schemas import TaskType


def test_benchmark_candidate_classification():
    df = pd.DataFrame({
        "num1": np.random.randn(100),
        "num2": np.random.randn(100),
        "cat1": ["A", "B"] * 50,
        "target": [0, 1] * 50,
    })
    res = benchmark_candidate(
        algorithm_name="RandomForestClassifier",
        df=df,
        target_col="target",
        task_type=TaskType.BINARY_CLASSIFICATION,
        cv_folds=3
    )
    assert res.status == "completed"
    assert res.score >= 0.0
    assert len(res.cv_scores) == 3


def test_benchmark_candidate_regression():
    df = pd.DataFrame({
        "num1": np.random.randn(100),
        "target": np.random.randn(100) * 10,
    })
    res = benchmark_candidate(
        algorithm_name="Ridge",
        df=df,
        target_col="target",
        task_type=TaskType.REGRESSION,
        cv_folds=3
    )
    assert res.status == "completed"
    assert res.metric == "r2"
