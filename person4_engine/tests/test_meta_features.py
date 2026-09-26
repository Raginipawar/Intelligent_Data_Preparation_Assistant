"""
test_meta_features.py — Tests meta-feature extraction logic across classification, regression, and imbalanced datasets.
"""
import numpy as np
import pandas as pd
from app.meta_features import extract_meta_features
from app.recommend_schemas import TaskType


def test_meta_features_binary_classification():
    df = pd.DataFrame({
        "num1": np.random.randn(100),
        "num2": np.random.randn(100),
        "cat1": ["a", "b"] * 50,
        "target": [0, 1] * 50,
    })
    mf = extract_meta_features(df, target_col="target")
    assert mf.n_rows == 100
    assert mf.n_columns == 4
    assert mf.n_features == 3
    assert mf.task_type == TaskType.BINARY_CLASSIFICATION
    assert mf.class_imbalance_ratio == 1.0


def test_meta_features_regression():
    df = pd.DataFrame({
        "num1": np.random.randn(100),
        "num2": np.random.randn(100),
        "target": np.random.randn(100) * 100,
    })
    mf = extract_meta_features(df, target_col="target")
    assert mf.n_rows == 100
    assert mf.task_type == TaskType.REGRESSION


def test_meta_features_imbalanced_classification():
    df = pd.DataFrame({
        "f1": np.random.randn(100),
        "target": [0] * 90 + [1] * 10,
    })
    mf = extract_meta_features(df, target_col="target")
    assert mf.task_type == TaskType.BINARY_CLASSIFICATION
    assert mf.class_imbalance_ratio == 9.0
