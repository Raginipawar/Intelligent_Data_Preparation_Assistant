import pytest

from app.dataset_client import DatasetUnavailable, resolve_dataset, store_own_dataset
from app.suggestion_client import SuggestionListUnavailable, resolve_suggestions
from app.apply_schemas import ApplyRequest, SuggestionIn


def test_sample_df_shape(sample_df):
    assert len(sample_df) == 200
    assert set(sample_df.columns) == {
        "tenure_months", "monthly_charges", "total_charges", "age", "contract",
        "signup_channel", "customer_id", "is_autopay", "churned",
    }
    assert sample_df["monthly_charges"].isna().sum() > 0


def test_sample_suggestions_cover_every_type(sample_suggestions):
    types = {s["type"] for s in sample_suggestions}
    assert types == {
        "imputation", "encoding", "scaling", "transform", "drop_redundant", "binning", "interaction",
    }
    ids = [s["id"] for s in sample_suggestions]
    assert len(ids) == len(set(ids))


def test_suggestion_in_tolerant_of_extra_fields():
    s = SuggestionIn(
        id="x", type="imputation", target_columns=["a"], params={"strategy": "mean"},
        some_future_field="should not crash",
    )
    assert s.id == "x"
    assert s.params["strategy"] == "mean"


def test_resolve_dataset_round_trip(sample_df):
    dataset_id = store_own_dataset(sample_df, source_type="single_csv", primary_file="fake.csv")
    df, source_type, primary_file = resolve_dataset(dataset_id)
    assert len(df) == len(sample_df)
    assert source_type == "single_csv"
    assert primary_file == "fake.csv"


def test_resolve_dataset_missing_raises():
    with pytest.raises(DatasetUnavailable):
        resolve_dataset("does-not-exist")


def test_resolve_suggestions_inline(sample_suggestions):
    result = resolve_suggestions(inline_suggestions=sample_suggestions)
    assert result == sample_suggestions


def test_resolve_suggestions_missing_raises():
    with pytest.raises(SuggestionListUnavailable):
        resolve_suggestions(source_job_id="does-not-exist")


def test_apply_request_requires_dataset_and_selection():
    req = ApplyRequest(dataset_id="d1", selected_suggestion_ids=["imputation_age"])
    assert req.feature_budget is None
    assert req.suggestions is None
