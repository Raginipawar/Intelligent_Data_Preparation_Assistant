"""
Unit tests for each rule module in app/suggestions/, using small hand-built
dicts shaped like Person 1's Dataset Health Report sections (rather than the
full fixture) so each test's expected outcome is easy to verify by inspection.

Run: pytest -v tests/test_rules.py
"""
from app.suggestions.binning_rules import build_binning_suggestions
from app.suggestions.encoding_rules import build_encoding_suggestions
from app.suggestions.interaction_rules import build_interaction_suggestions
from app.suggestions.missingness_rules import build_imputation_suggestions
from app.suggestions.redundancy import build_correlated_cluster_suggestions, build_identifier_drop_suggestions
from app.suggestions.scaling_rules import build_scaling_suggestions
from app.suggestions.transform_rules import build_transform_suggestions


# --- imputation ---------------------------------------------------------


def test_imputation_numeric_skewed_uses_median():
    missingness = {"columns": {"income": {"missing_count": 50, "missing_pct": 10.0}}, "co_missing_pairs": []}
    distributions = {"columns": {"income": {"skewness": 2.5, "std": 100}}}
    schema_columns = [{"name": "income", "inferred_dtype": "numeric_float"}]

    suggestions = build_imputation_suggestions(missingness, distributions, schema_columns)
    assert len(suggestions) == 1
    assert suggestions[0].params == {"strategy": "median"}
    assert "skew" in suggestions[0].reasoning.lower()


def test_imputation_numeric_symmetric_uses_mean():
    missingness = {"columns": {"age": {"missing_count": 20, "missing_pct": 4.0}}, "co_missing_pairs": []}
    distributions = {"columns": {"age": {"skewness": 0.1, "std": 10}}}
    schema_columns = [{"name": "age", "inferred_dtype": "numeric_int"}]

    suggestions = build_imputation_suggestions(missingness, distributions, schema_columns)
    assert suggestions[0].params == {"strategy": "mean"}


def test_imputation_categorical_high_missing_uses_constant_not_mode():
    missingness = {"columns": {"channel": {"missing_count": 600, "missing_pct": 30.0}}, "co_missing_pairs": []}
    distributions = {"columns": {}}
    schema_columns = [{"name": "channel", "inferred_dtype": "categorical"}]

    suggestions = build_imputation_suggestions(missingness, distributions, schema_columns)
    assert suggestions[0].params["strategy"] == "constant"


def test_imputation_zero_missing_column_is_skipped():
    missingness = {"columns": {"id": {"missing_count": 0, "missing_pct": 0.0}}, "co_missing_pairs": []}
    schema_columns = [{"name": "id", "inferred_dtype": "numeric_int"}]
    suggestions = build_imputation_suggestions(missingness, {"columns": {}}, schema_columns)
    assert suggestions == []


def test_imputation_co_missing_partner_noted_in_reasoning():
    missingness = {
        "columns": {
            "ship_date": {"missing_count": 100, "missing_pct": 20.0},
            "shipped_flag": {"missing_count": 100, "missing_pct": 20.0},
        },
        "co_missing_pairs": [{"col1": "ship_date", "col2": "shipped_flag", "co_missing_rows": 100, "jaccard": 0.95}],
    }
    distributions = {"columns": {}}
    schema_columns = [
        {"name": "ship_date", "inferred_dtype": "boolean"},
        {"name": "shipped_flag", "inferred_dtype": "boolean"},
    ]
    suggestions = build_imputation_suggestions(missingness, distributions, schema_columns)
    ship_date_suggestion = next(s for s in suggestions if s.target_columns == ["ship_date"])
    assert "co-occurs" in ship_date_suggestion.reasoning


# --- encoding ------------------------------------------------------------


def test_encoding_low_cardinality_uses_onehot():
    cardinality = {"columns": {"contract": {"n_unique": 3, "unique_ratio": 0.001, "high_cardinality": False}}}
    schema_columns = [{"name": "contract", "inferred_dtype": "categorical"}]
    suggestions = build_encoding_suggestions(cardinality, schema_columns, {})
    assert suggestions[0].params == {"method": "onehot"}


def test_encoding_moderate_cardinality_with_target_uses_target_encoding():
    cardinality = {"columns": {"city": {"n_unique": 40, "unique_ratio": 0.05, "high_cardinality": False}}}
    schema_columns = [{"name": "city", "inferred_dtype": "categorical"}]
    suggestions = build_encoding_suggestions(cardinality, schema_columns, {"suggested_target": "churned"})
    assert suggestions[0].params["method"] == "target"


def test_encoding_moderate_cardinality_without_target_uses_frequency():
    cardinality = {"columns": {"city": {"n_unique": 40, "unique_ratio": 0.05, "high_cardinality": False}}}
    schema_columns = [{"name": "city", "inferred_dtype": "categorical"}]
    suggestions = build_encoding_suggestions(cardinality, schema_columns, {})
    assert suggestions[0].params["method"] == "frequency"


def test_encoding_skips_columns_already_flagged_high_cardinality():
    cardinality = {"columns": {"user_uuid": {"n_unique": 9990, "unique_ratio": 0.999, "high_cardinality": True}}}
    schema_columns = [{"name": "user_uuid", "inferred_dtype": "categorical"}]
    suggestions = build_encoding_suggestions(cardinality, schema_columns, {})
    assert suggestions == []  # handled by redundancy.build_identifier_drop_suggestions instead


# --- scaling ---------------------------------------------------------------


def test_scaling_outlier_involved_column_uses_robust():
    distributions = {"columns": {"income": {"std": 500}}}
    outliers = {"isolation_forest": {"column_involvement": {"income": 15}}}
    suggestions = build_scaling_suggestions(distributions, outliers)
    assert suggestions[0].params == {"method": "robust"}


def test_scaling_clean_column_uses_standard():
    distributions = {"columns": {"age": {"std": 12}}}
    outliers = {"isolation_forest": {"column_involvement": {"age": 0}}}
    suggestions = build_scaling_suggestions(distributions, outliers)
    assert suggestions[0].params == {"method": "standard"}


def test_scaling_skips_degenerate_column():
    distributions = {"columns": {"constant_col": {"std": 0}}}
    suggestions = build_scaling_suggestions(distributions, {})
    assert suggestions == []


# --- transform ---------------------------------------------------------------


def test_transform_positive_skewed_uses_log1p():
    distributions = {"columns": {"total_charges": {"skewness": 3.2, "min": 0.0}}}
    suggestions = build_transform_suggestions(distributions)
    assert suggestions[0].params == {"function": "log1p"}


def test_transform_skewed_with_negatives_uses_yeo_johnson():
    distributions = {"columns": {"balance": {"skewness": -2.0, "min": -500.0}}}
    suggestions = build_transform_suggestions(distributions)
    assert suggestions[0].params == {"function": "yeo_johnson"}


def test_transform_below_threshold_skipped():
    distributions = {"columns": {"age": {"skewness": 0.3, "min": 18}}}
    suggestions = build_transform_suggestions(distributions)
    assert suggestions == []


# --- redundancy: correlated clusters ----------------------------------------


def test_redundancy_correlated_pair_drops_lower_importance_member():
    correlation = {
        "matrix": {
            "monthly_charges": {"monthly_charges": 1.0, "total_charges": 0.95},
            "total_charges": {"monthly_charges": 0.95, "total_charges": 1.0},
        }
    }
    feature_importance_signal = {"importances": {"monthly_charges": 0.15, "total_charges": 0.42}}
    suggestions = build_correlated_cluster_suggestions(correlation, feature_importance_signal, {"columns": {}})
    assert len(suggestions) == 1
    assert suggestions[0].target_columns == ["monthly_charges"]
    assert suggestions[0].params["kept_column"] == "total_charges"


def test_redundancy_below_threshold_no_suggestion():
    correlation = {
        "matrix": {
            "a": {"a": 1.0, "b": 0.5},
            "b": {"a": 0.5, "b": 1.0},
        }
    }
    suggestions = build_correlated_cluster_suggestions(correlation, {}, {"columns": {}})
    assert suggestions == []


# --- redundancy: identifier drop --------------------------------------------


def test_identifier_drop_flags_high_cardinality_categorical():
    cardinality = {"columns": {"customer_id": {"n_unique": 5000, "unique_ratio": 1.0, "high_cardinality": True}}}
    schema_columns = [{"name": "customer_id", "inferred_dtype": "text_freeform"}]
    suggestions = build_identifier_drop_suggestions(cardinality, schema_columns, target_col=None)
    assert len(suggestions) == 1
    assert suggestions[0].params["reason"] == "high_cardinality_identifier"


def test_identifier_drop_excludes_continuous_numeric_float():
    cardinality = {"columns": {"price": {"n_unique": 4999, "unique_ratio": 0.999, "high_cardinality": True}}}
    schema_columns = [{"name": "price", "inferred_dtype": "numeric_float"}]
    suggestions = build_identifier_drop_suggestions(cardinality, schema_columns, target_col=None)
    assert suggestions == []


def test_identifier_drop_excludes_target_column():
    cardinality = {"columns": {"weird_target": {"n_unique": 5000, "unique_ratio": 1.0, "high_cardinality": True}}}
    schema_columns = [{"name": "weird_target", "inferred_dtype": "categorical"}]
    suggestions = build_identifier_drop_suggestions(cardinality, schema_columns, target_col="weird_target")
    assert suggestions == []


# --- binning ---------------------------------------------------------------


def test_binning_suggested_for_skewed_moderate_cardinality_column():
    distributions = {"columns": {"claims_count": {"skewness": 2.0}}}
    cardinality = {"columns": {"claims_count": {"n_unique": 25}}}
    suggestions = build_binning_suggestions(distributions, cardinality)
    assert len(suggestions) == 1
    assert suggestions[0].params == {"strategy": "quantile", "n_bins": 5}


def test_binning_skipped_for_continuous_high_cardinality_column():
    distributions = {"columns": {"total_charges": {"skewness": 3.2}}}
    cardinality = {"columns": {"total_charges": {"n_unique": 4870}}}
    suggestions = build_binning_suggestions(distributions, cardinality)
    assert suggestions == []


# --- interaction -------------------------------------------------------------


def test_interaction_pairs_top_importance_non_redundant_columns():
    feature_importance_signal = {"ran": True, "importances": {"a": 0.5, "b": 0.3, "c": 0.2}}
    correlation = {"matrix": {"a": {"b": 0.1}, "b": {"a": 0.1}}}
    suggestions = build_interaction_suggestions(feature_importance_signal, correlation)
    assert len(suggestions) > 0
    assert all(s.type.value == "interaction" for s in suggestions)


def test_interaction_skips_when_signal_did_not_run():
    feature_importance_signal = {"ran": False, "importances": {}}
    suggestions = build_interaction_suggestions(feature_importance_signal, {"matrix": {}})
    assert suggestions == []


def test_interaction_skips_highly_correlated_pair():
    feature_importance_signal = {"ran": True, "importances": {"a": 0.5, "b": 0.3}}
    correlation = {"matrix": {"a": {"b": 0.95}, "b": {"a": 0.95}}}
    suggestions = build_interaction_suggestions(feature_importance_signal, correlation)
    assert suggestions == []
