import pandas as pd

from app.apply.conflict_resolution import resolve_conflicts
from app.apply.feature_selection import apply_feature_budget


def _s(id, type, target_columns, priority_rank=1, **params):
    return {"id": id, "type": type, "target_columns": target_columns, "priority_rank": priority_rank, "params": params}


def test_same_type_collision_keeps_higher_priority():
    suggestions = [
        _s("scaling_age", "scaling", ["age"], priority_rank=7, method="standard"),
        _s("scaling_age_2", "scaling", ["age"], priority_rank=8, method="robust"),
    ]
    kept, skipped = resolve_conflicts(suggestions)
    assert [s["id"] for s in kept] == ["scaling_age"]
    assert skipped[0]["suggestion_id"] == "scaling_age_2"
    assert "scaling_age" in skipped[0]["reasoning"]


def test_no_conflict_for_distinct_columns():
    suggestions = [
        _s("scaling_age", "scaling", ["age"], priority_rank=1, method="standard"),
        _s("scaling_charges", "scaling", ["monthly_charges"], priority_rank=2, method="robust"),
    ]
    kept, skipped = resolve_conflicts(suggestions)
    assert len(kept) == 2
    assert skipped == []


def test_onehot_encoding_conflicts_with_later_touch_on_same_column():
    suggestions = [
        _s("encoding_contract", "encoding", ["contract"], priority_rank=1, method="onehot"),
        _s("scaling_contract", "scaling", ["contract"], priority_rank=2, method="standard"),
    ]
    kept, skipped = resolve_conflicts(suggestions)
    assert [s["id"] for s in kept] == ["encoding_contract"]
    assert skipped[0]["suggestion_id"] == "scaling_contract"


def test_imputation_not_flagged_as_conflicting_with_later_onehot_encoding():
    # Regression test: imputation runs BEFORE encoding in the pipeline, so
    # impute-then-onehot-encode on the same column is a normal, valid
    # combination — not a conflict. (This was a real bug: rule 2 originally
    # flagged any non-encoding suggestion on the onehot'd column, imputation
    # included, and it was only caught via live three-engine integration
    # testing against a real dataset.)
    suggestions = [
        _s("imputation_contract", "imputation", ["contract"], priority_rank=1, strategy="mode"),
        _s("encoding_contract", "encoding", ["contract"], priority_rank=2, method="onehot"),
    ]
    kept, skipped = resolve_conflicts(suggestions)
    assert {s["id"] for s in kept} == {"imputation_contract", "encoding_contract"}
    assert skipped == []


def test_drop_redundant_not_flagged_as_conflicting_with_earlier_stage():
    # drop_redundant runs last in pipeline order, so it isn't a real conflict
    # with e.g. an imputation suggestion on the same (soon-to-be-dropped) column.
    suggestions = [
        _s("imputation_x", "imputation", ["x"], priority_rank=1, strategy="mean"),
        _s("drop_x", "drop_redundant", ["x"], priority_rank=2, reason="correlated_redundancy"),
    ]
    kept, skipped = resolve_conflicts(suggestions)
    assert {s["id"] for s in kept} == {"imputation_x", "drop_x"}
    assert skipped == []


def test_feature_budget_no_op_when_under_budget():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result_df, entries = apply_feature_budget(df, {}, feature_budget=5)
    assert list(result_df.columns) == ["a", "b"]
    assert entries == []


def test_feature_budget_drops_highest_tier_first():
    df = pd.DataFrame({"raw": [1], "binned": [1], "interaction": [1]})
    registry = {
        "binned": {"tier": 2, "confidence": 0.5, "source_suggestion_id": "binning_x"},
        "interaction": {"tier": 3, "confidence": 0.5, "source_suggestion_id": "interaction_x"},
    }
    result_df, entries = apply_feature_budget(df, registry, feature_budget=2)
    assert list(result_df.columns) == ["raw", "binned"]
    assert len(entries) == 1
    assert entries[0]["column"] == "interaction"


def test_feature_budget_never_drops_raw_columns():
    df = pd.DataFrame({"raw1": [1], "raw2": [2]})
    result_df, entries = apply_feature_budget(df, {}, feature_budget=1)
    assert list(result_df.columns) == ["raw1", "raw2"]
    assert entries[0]["column"] is None
    assert "could not be fully satisfied" in entries[0]["reasoning"]
