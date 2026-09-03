"""
Integration tests: the full rule-engine orchestration (generate_suggestions)
against the synthetic fixture in sample_data/fake_health_report.py, plus
pipeline.run_suggestion_job's input-resolution behavior.

Run: pytest -v tests/test_pipeline.py
"""
import pytest

from app.health_report_client import HealthReportUnavailable
from app.suggestion_pipeline import run_suggestion_job
from app.suggestions.suggestion_builder import generate_suggestions


def test_generate_suggestions_produces_expected_types(health_report):
    result = generate_suggestions(health_report, df=None, dataset_id="ds1", source_job_id="job1", job_id="sjob1")

    assert result["dataset_id"] == "ds1"
    assert result["status"] == "success"
    types_present = {s["type"] for s in result["suggestions"]}
    assert {"imputation", "encoding", "scaling", "transform", "drop_redundant", "interaction"} <= types_present


def test_generate_suggestions_ids_are_unique_and_stable_slugs():
    from sample_data.fake_health_report import build_fake_health_report

    result = generate_suggestions(build_fake_health_report(), df=None, dataset_id="ds1", source_job_id="job1")
    ids = [s["id"] for s in result["suggestions"]]
    assert len(ids) == len(set(ids))
    assert all(isinstance(i, str) and i for i in ids)


def test_generate_suggestions_priority_rank_is_dense_and_ordered(health_report):
    result = generate_suggestions(health_report, df=None, dataset_id="ds1", source_job_id="job1")
    ranks = [s["priority_rank"] for s in result["suggestions"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_generate_suggestions_finds_the_correlated_redundant_pair(health_report):
    result = generate_suggestions(health_report, df=None, dataset_id="ds1", source_job_id="job1")
    drop_suggestions = [s for s in result["suggestions"] if s["type"] == "drop_redundant"]
    targets = [tuple(s["target_columns"]) for s in drop_suggestions]
    assert ("monthly_charges",) in targets  # dropped in favor of higher-importance total_charges
    assert ("customer_id",) in targets  # near-unique identifier


def test_automl_enrichment_degrades_gracefully_without_autogluon_installed(health_report):
    # autogluon.features isn't in requirements.txt's required (non-commented) deps,
    # so on a stock install this should degrade cleanly rather than raising.
    result = generate_suggestions(health_report, df=None, dataset_id="ds1", source_job_id="job1")
    assert "automl_enrichment" in result
    assert result["automl_enrichment"]["autogluon"]["ran"] in (True, False)


def test_pipeline_uses_inline_report_without_touching_disk(health_report):
    result = run_suggestion_job(dataset_id="ds1", job_id="sjob1", source_job_id=None, inline_report=health_report)
    assert result["dataset_id"] == "ds1"
    assert result["job_id"] == "sjob1"

    from app import suggestion_config as config

    output_path = config.SUGGESTIONS_DIR / "sjob1.json"
    assert output_path.exists()


def test_pipeline_raises_clear_error_with_no_report_available():
    with pytest.raises(HealthReportUnavailable):
        run_suggestion_job(dataset_id="ds-missing", job_id="sjob-missing", source_job_id="no-such-job", inline_report=None)
