from app.apply.orchestrator import run_orchestration


def test_full_pipeline_applies_everything_when_all_selected(sample_df, sample_suggestions):
    all_ids = [s["id"] for s in sample_suggestions]
    result = run_orchestration(sample_df, sample_suggestions, all_ids, feature_budget=None, target_col="churned")

    df = result["df"]
    log = result["transformation_log"]
    applied = result["applied_suggestions"]
    skipped = result["skipped_suggestions"]

    # no missing values remain in the columns we imputed and kept
    assert df["age"].isna().sum() == 0

    # onehot encoding removed 'contract' and added dummy columns
    assert "contract" not in df.columns
    assert any(c.startswith("contract_") for c in df.columns)

    # 'monthly_charges' was imputed (order 1) then dropped as redundant (order last) —
    # both steps ran, the column just doesn't survive to the final frame.
    imputation_entry = next(e for e in log if e["suggestion_id"] == "imputation_monthly_charges")
    assert imputation_entry["status"] == "applied"
    assert "monthly_charges" not in df.columns
    assert "customer_id" not in df.columns

    # engineered columns present
    assert "tenure_months_binned" in df.columns
    assert "age_x_tenure_months" in df.columns

    # the deliberate scaling conflict resolved to the higher-priority suggestion
    assert "scaling_age" in applied
    assert "scaling_age_2" not in applied
    conflict_entries = [s for s in skipped if s["suggestion_id"] == "scaling_age_2"]
    assert conflict_entries and conflict_entries[0]["status"] == "skipped_conflict"

    # log is ordered and covers every processed suggestion
    orders = [entry["order"] for entry in log]
    assert orders == sorted(orders)
    assert orders == list(range(1, len(log) + 1))


def test_partial_selection_only_applies_chosen_suggestions(sample_df, sample_suggestions):
    selected = ["imputation_age", "scaling_age"]
    result = run_orchestration(sample_df, sample_suggestions, selected, feature_budget=None)

    assert result["applied_suggestions"] == ["imputation_age", "scaling_age"]
    not_selected = [s for s in result["skipped_suggestions"] if s["status"] == "skipped_not_selected"]
    assert len(not_selected) == len(sample_suggestions) - 2

    df = result["df"]
    assert df["age"].isna().sum() == 0
    assert "monthly_charges" in df.columns  # drop_redundant wasn't selected
    assert "customer_id" in df.columns


def test_unknown_selected_id_is_logged_not_crashed(sample_df, sample_suggestions):
    result = run_orchestration(sample_df, sample_suggestions, ["does_not_exist"], feature_budget=None)
    assert result["applied_suggestions"] == []
    errors = [s for s in result["skipped_suggestions"] if s["suggestion_id"] == "does_not_exist"]
    assert errors and errors[0]["status"] == "skipped_error"


def test_target_col_is_threaded_through_to_target_encoding(sample_df, sample_suggestions):
    # Regression test: run_apply_job previously never passed target_col through
    # to run_orchestration, so `encoding` suggestions with method="target"
    # always silently degraded to frequency encoding even when a real target
    # column was available. Confirm it's actually used when supplied.
    suggestions = sample_suggestions + [
        {
            "id": "encoding_contract_target", "type": "encoding", "target_columns": ["contract"],
            "priority_rank": 1, "params": {"method": "target"}, "confidence": 0.7,
        }
    ]
    result = run_orchestration(
        sample_df, suggestions, ["encoding_contract_target"], feature_budget=None, target_col="churned",
    )
    entry = next(e for e in result["transformation_log"] if e["suggestion_id"] == "encoding_contract_target")
    assert entry["status"] == "applied"
    assert "target-encoded" in entry["action"]
    assert "no usable target column" not in entry["action"]


def test_feature_budget_trims_engineered_columns(sample_df, sample_suggestions):
    all_ids = [s["id"] for s in sample_suggestions]
    n_cols_unbudgeted = len(run_orchestration(sample_df, sample_suggestions, all_ids)["df"].columns)

    result = run_orchestration(sample_df, sample_suggestions, all_ids, feature_budget=n_cols_unbudgeted - 2)
    df = result["df"]
    assert len(df.columns) <= n_cols_unbudgeted - 2
    budget_log = [e for e in result["transformation_log"] if e["status"] == "budget_drop"]
    assert len(budget_log) >= 2
    # interaction (tier 3) should be trimmed before binning (tier 2)
    assert "age_x_tenure_months" not in df.columns
