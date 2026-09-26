import numpy as np
import pandas as pd
import pytest

from app.apply.binning import apply_binning
from app.apply.drop_redundant import apply_drop_redundant
from app.apply.encoding import apply_encoding
from app.apply.imputation import apply_imputation
from app.apply.interaction import apply_interaction
from app.apply.scaling import apply_scaling
from app.apply.transform import apply_transform


def test_imputation_median():
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
    suggestion = {"target_columns": ["x"], "params": {"strategy": "median"}}
    df, action = apply_imputation(df, suggestion)
    assert df["x"].isna().sum() == 0
    assert df.loc[2, "x"] == 2.0  # median of [1,2,4]
    assert "median" in action


def test_imputation_constant_with_fill_value():
    df = pd.DataFrame({"x": ["a", None, "b"]})
    suggestion = {"target_columns": ["x"], "params": {"strategy": "constant", "fill_value": "unknown"}}
    df, _ = apply_imputation(df, suggestion)
    assert df["x"].tolist() == ["a", "unknown", "b"]


def test_imputation_unknown_strategy_raises():
    df = pd.DataFrame({"x": [1.0, np.nan]})
    with pytest.raises(ValueError):
        apply_imputation(df, {"target_columns": ["x"], "params": {"strategy": "bogus"}})


def test_encoding_onehot():
    df = pd.DataFrame({"c": ["a", "b", "a"]})
    suggestion = {"target_columns": ["c"], "params": {"method": "onehot"}}
    df, action = apply_encoding(df, suggestion)
    assert "c" not in df.columns
    assert {"c_a", "c_b"}.issubset(df.columns)
    assert "one-hot" in action


def test_encoding_frequency():
    df = pd.DataFrame({"c": ["a", "a", "b"]})
    df, _ = apply_encoding(df, {"target_columns": ["c"], "params": {"method": "frequency"}})
    assert df["c"].tolist() == pytest.approx([2 / 3, 2 / 3, 1 / 3])


def test_encoding_target_falls_back_without_target_column():
    df = pd.DataFrame({"c": ["a", "a", "b"]})
    df, action = apply_encoding(df, {"target_columns": ["c"], "params": {"method": "target"}}, target_col=None)
    assert "no usable target column" in action


def test_encoding_target_with_target_column():
    df = pd.DataFrame({"c": ["a", "a", "b"], "y": [1, 0, 1]})
    df, action = apply_encoding(df, {"target_columns": ["c"], "params": {"method": "target"}}, target_col="y")
    assert df["c"].tolist() == pytest.approx([0.5, 0.5, 1.0])


def test_scaling_standard_and_robust():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 100.0]})
    scaled_std, _ = apply_scaling(df.copy(), {"target_columns": ["x"], "params": {"method": "standard"}})
    scaled_rob, _ = apply_scaling(df.copy(), {"target_columns": ["x"], "params": {"method": "robust"}})
    assert scaled_std["x"].mean() == pytest.approx(0.0, abs=1e-9)
    assert not scaled_std["x"].equals(scaled_rob["x"])


def test_transform_log1p():
    df = pd.DataFrame({"x": [0.0, 1.0, np.e - 1]})
    df, action = apply_transform(df, {"target_columns": ["x"], "params": {"function": "log1p"}})
    assert df["x"].iloc[0] == pytest.approx(0.0)
    assert "log1p" in action


def test_transform_yeo_johnson():
    df = pd.DataFrame({"x": [-2.0, -1.0, 0.0, 1.0, 2.0, 50.0]})
    df, action = apply_transform(df, {"target_columns": ["x"], "params": {"function": "yeo_johnson"}})
    assert df["x"].std() < 50  # normalized away the extreme skew
    assert "Yeo-Johnson" in action


def test_binning_quantile():
    df = pd.DataFrame({"x": list(range(20))})
    df, action = apply_binning(df, {"target_columns": ["x"], "params": {"strategy": "quantile", "n_bins": 4}})
    assert "x_binned" in df.columns
    assert df["x_binned"].nunique() == 4
    assert "x" in df.columns  # original retained


def test_binning_collapses_bins_for_low_cardinality():
    df = pd.DataFrame({"x": [1, 1, 1, 1, 1]})
    df, _ = apply_binning(df, {"target_columns": ["x"], "params": {"strategy": "quantile", "n_bins": 4}})
    assert df["x_binned"].nunique() == 1


def test_interaction_multiply():
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    suggestion = {"target_columns": ["a", "b"], "params": {"operation": "multiply", "new_column": "a_x_b"}}
    df, action = apply_interaction(df, suggestion)
    assert df["a_x_b"].tolist() == [3.0, 8.0]


def test_interaction_requires_exactly_two_columns():
    df = pd.DataFrame({"a": [1.0], "b": [2.0], "c": [3.0]})
    with pytest.raises(ValueError):
        apply_interaction(df, {"target_columns": ["a", "b", "c"], "params": {"operation": "multiply"}})


def test_drop_redundant():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    df, action = apply_drop_redundant(df, {"target_columns": ["a", "b"], "params": {"reason": "correlated_redundancy", "kept_column": "c"}})
    assert list(df.columns) == ["c"]
    assert "kept 'c'" in action


def test_drop_redundant_already_absent_is_noop():
    df = pd.DataFrame({"a": [1]})
    df, action = apply_drop_redundant(df, {"target_columns": ["ghost"], "params": {}})
    assert list(df.columns) == ["a"]
    assert "already absent" in action
