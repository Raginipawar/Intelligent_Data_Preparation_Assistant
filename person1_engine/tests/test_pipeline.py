"""
End-to-end tests: run the full ingest -> analyze pipeline against the
synthetic messy dataset and against small edge-case DataFrames, and sanity
check the resulting Dataset Health Report against the pydantic contract.

Run: pytest -v tests/test_pipeline.py
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from app import pipeline
from app.schemas import DatasetHealthReport

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "sample_data" / "customer_churn_messy.csv"


@pytest.fixture(scope="module")
def analyzed_report():
    raw_bytes = SAMPLE_CSV.read_bytes()
    ingest_result = pipeline.ingest_upload(raw_bytes, "customer_churn_messy.csv")
    dataset_id = ingest_result["dataset_id"]
    report = pipeline.run_full_analysis(dataset_id, job_id="test-job-1")
    return ingest_result, report


def test_ingestion_parses_expected_shape(analyzed_report):
    ingest_result, _ = analyzed_report
    ing = ingest_result["ingestion"]
    # 1220 generated rows + 20 dupes already counted in that + 1 malformed line dropped
    assert ing["n_rows"] == 1220
    assert ing["n_columns"] == 12
    assert ing["malformed_rows_skipped"] == 1
    assert ing["source_type"] == "single_csv"


def test_dtype_inference_reasonable(analyzed_report):
    ingest_result, _ = analyzed_report
    dtypes = {c["name"]: c["inferred_dtype"] for c in ingest_result["schema"]["columns"]}
    assert dtypes["tenure_months"] in ("numeric_int", "numeric_float")
    assert dtypes["monthly_charges"] == "numeric_float"
    assert dtypes["gender"] == "categorical"
    assert dtypes["contract"] == "categorical"
    assert dtypes["signup_date"] == "datetime"
    assert dtypes["support_notes"] == "text_freeform"
    assert dtypes["customer_id"] == "text_freeform"  # unique per row -> not categorical
    # total_charges has injected " " strings among numbers -> mixed type flag should fire
    mixed_flags = {c["name"]: c["mixed_type_flag"] for c in ingest_result["schema"]["columns"]}
    assert mixed_flags["total_charges"] is True


def test_report_matches_pydantic_contract(analyzed_report):
    _, report = analyzed_report
    # This is the real integration check: if this validates, Person 2 can
    # deserialize our JSON straight into DatasetHealthReport without surprises.
    validated = DatasetHealthReport.model_validate(report)
    assert validated.dataset_id == report["dataset_id"]


def test_missingness_detected(analyzed_report):
    _, report = analyzed_report
    total_charges_missing = report["missingness"]["columns"]["total_charges"]["missing_pct"]
    support_notes_missing = report["missingness"]["columns"]["support_notes"]["missing_pct"]
    assert total_charges_missing > 0
    assert support_notes_missing > 30  # ~35% injected + Nones


def test_duplicates_detected(analyzed_report):
    _, report = analyzed_report
    assert report["duplicates"]["exact_duplicate_rows"] >= 20


def test_target_detection_finds_churned(analyzed_report):
    _, report = analyzed_report
    assert report["target_detection"]["suggested_target"] == "churned"
    assert report["target_detection"]["task_type_guess"] == "classification"


def test_outliers_flag_injected_extremes(analyzed_report):
    _, report = analyzed_report
    assert report["outliers"]["isolation_forest"] is not None
    assert len(report["outliers"]["isolation_forest"]["flagged_row_indices"]) > 0
    assert report["outliers"]["distance_baseline"] is not None
    assert report["outliers"]["agreement_rate"] is not None


def test_surrogate_model_ran_and_ranks_signal_features(analyzed_report):
    _, report = analyzed_report
    sig = report["feature_importance_signal"]
    assert sig["ran"] is True
    assert sig["target_used"] == "churned"
    # tenure_months and contract were the actual drivers we baked into churn_score
    top_features = list(sig["importances"].keys())[:4]
    assert "tenure_months" in top_features or "contract" in top_features


def test_correlation_matrix_present(analyzed_report):
    _, report = analyzed_report
    assert "tenure_months" in report["correlation"]["matrix"]
    assert "monthly_charges" in report["correlation"]["matrix"]["tenure_months"]


# --- Edge cases ---


def test_tiny_dataset_does_not_crash(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    csv_path = tmp_path / "tiny.csv"
    df.to_csv(csv_path, index=False)
    ingest_result = pipeline.ingest_upload(csv_path.read_bytes(), "tiny.csv")
    report = pipeline.run_full_analysis(ingest_result["dataset_id"], job_id="test-tiny")
    # too few rows for Isolation Forest / surrogate -> should degrade gracefully, not crash
    assert report["outliers"]["isolation_forest"] is None
    assert report["feature_importance_signal"]["ran"] is False


def test_no_numeric_columns_does_not_crash(tmp_path):
    df = pd.DataFrame({"a": ["cat", "dog", "cat", "bird"] * 10, "b": ["x", "y", "x", "z"] * 10})
    csv_path = tmp_path / "cats.csv"
    df.to_csv(csv_path, index=False)
    ingest_result = pipeline.ingest_upload(csv_path.read_bytes(), "cats.csv")
    report = pipeline.run_full_analysis(ingest_result["dataset_id"], job_id="test-cats")
    assert report["distributions"]["columns"] == {}
    assert report["correlation"]["matrix"] == {}


def test_all_missing_column_does_not_crash(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5] * 5, "b": [None] * 25})
    csv_path = tmp_path / "allnull.csv"
    df.to_csv(csv_path, index=False)
    ingest_result = pipeline.ingest_upload(csv_path.read_bytes(), "allnull.csv")
    report = pipeline.run_full_analysis(ingest_result["dataset_id"], job_id="test-allnull")
    assert report["missingness"]["columns"]["b"]["missing_pct"] == 100.0
