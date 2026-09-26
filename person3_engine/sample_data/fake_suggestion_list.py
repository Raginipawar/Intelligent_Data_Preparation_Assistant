"""
fake_suggestion_list.py — a synthetic Suggestion List matching Person 2's
`/suggest` output contract (app/suggestion_schemas.py::SuggestionList at the
repo root), shaped to pair with sample_data/fake_dataset.py's columns and to
exercise every rule this engine implements:

  - imputation (median/mode/mean) on monthly_charges/signup_channel/age/is_autopay
  - encoding (onehot/frequency) on contract/signup_channel
  - scaling — TWO competing suggestions on 'age' (standard vs. robust, ranks 7
    and 8) to exercise conflict_resolution.py: the higher-priority one (lower
    rank number) should win
  - transform (log1p) on total_charges
  - drop_redundant — correlated pair (monthly_charges, kept=total_charges) and
    a high-cardinality identifier (customer_id)
  - binning (quantile) on tenure_months
  - interaction (multiply) between age and tenure_months

Run directly to write sample_data/fake_suggestion_list.json:

    python sample_data/fake_suggestion_list.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def build_fake_suggestions() -> List[Dict[str, Any]]:
    return [
        {
            "id": "imputation_monthly_charges",
            "type": "imputation",
            "target_columns": ["monthly_charges"],
            "reasoning": "'monthly_charges' is missing in ~8% of rows; roughly symmetric, so median imputation.",
            "expected_impact": "low — fills a small gap in 'monthly_charges'",
            "priority_rank": 1,
            "params": {"strategy": "median"},
            "source": "rule_based",
            "confidence": 0.8,
        },
        {
            "id": "imputation_signup_channel",
            "type": "imputation",
            "target_columns": ["signup_channel"],
            "reasoning": "'signup_channel' is missing in ~12% of rows; mode imputation for a lightly-missing categorical.",
            "expected_impact": "low — fills a gap in 'signup_channel'",
            "priority_rank": 2,
            "params": {"strategy": "mode"},
            "source": "rule_based",
            "confidence": 0.75,
        },
        {
            "id": "imputation_age",
            "type": "imputation",
            "target_columns": ["age"],
            "reasoning": "'age' is missing in ~2% of rows; roughly symmetric, so mean imputation.",
            "expected_impact": "low — fills a small gap in 'age'",
            "priority_rank": 3,
            "params": {"strategy": "mean"},
            "source": "rule_based",
            "confidence": 0.8,
        },
        {
            "id": "imputation_is_autopay",
            "type": "imputation",
            "target_columns": ["is_autopay"],
            "reasoning": "'is_autopay' is missing in ~4% of rows; boolean mode-fill.",
            "expected_impact": "low — fills a gap in 'is_autopay'",
            "priority_rank": 4,
            "params": {"strategy": "mode"},
            "source": "rule_based",
            "confidence": 0.75,
        },
        {
            "id": "encoding_contract",
            "type": "encoding",
            "target_columns": ["contract"],
            "reasoning": "'contract' has low cardinality (3) — one-hot encoding.",
            "expected_impact": "medium — expands 'contract' into 3 binary columns",
            "priority_rank": 5,
            "params": {"method": "onehot"},
            "source": "rule_based",
            "confidence": 0.85,
        },
        {
            "id": "encoding_signup_channel",
            "type": "encoding",
            "target_columns": ["signup_channel"],
            "reasoning": "'signup_channel' has moderate cardinality — frequency encoding.",
            "expected_impact": "medium — replaces 'signup_channel' with its frequency",
            "priority_rank": 6,
            "params": {"method": "frequency"},
            "source": "rule_based",
            "confidence": 0.7,
        },
        {
            "id": "scaling_age",
            "type": "scaling",
            "target_columns": ["age"],
            "reasoning": "'age' is not outlier-involved — standard scaling.",
            "expected_impact": "low — rescales 'age'",
            "priority_rank": 7,
            "params": {"method": "standard"},
            "source": "rule_based",
            "confidence": 0.6,
        },
        {
            "id": "scaling_age_2",
            "type": "scaling",
            "target_columns": ["age"],
            "reasoning": (
                "'age' co-occurs with flagged outlier rows — robust scaling. "
                "(Deliberately conflicts with 'scaling_age' above to exercise conflict resolution.)"
            ),
            "expected_impact": "low — rescales 'age' with outlier-resistant statistics",
            "priority_rank": 8,
            "params": {"method": "robust"},
            "source": "rule_based",
            "confidence": 0.55,
        },
        {
            "id": "transform_total_charges",
            "type": "transform",
            "target_columns": ["total_charges"],
            "reasoning": "'total_charges' is heavily right-skewed and non-negative — log1p transform.",
            "expected_impact": "medium — normalizes 'total_charges' distribution",
            "priority_rank": 9,
            "params": {"function": "log1p"},
            "source": "rule_based",
            "confidence": 0.8,
        },
        {
            "id": "drop_redundant_monthly_charges",
            "type": "drop_redundant",
            "target_columns": ["monthly_charges"],
            "reasoning": "'monthly_charges' is highly correlated with 'total_charges' (r=0.93); keeping the higher-importance column.",
            "expected_impact": "medium — removes a redundant feature",
            "priority_rank": 10,
            "params": {"reason": "correlated_redundancy", "cluster": ["monthly_charges", "total_charges"], "kept_column": "total_charges"},
            "source": "rule_based",
            "confidence": 0.85,
        },
        {
            "id": "drop_redundant_customer_id",
            "type": "drop_redundant",
            "target_columns": ["customer_id"],
            "reasoning": "'customer_id' is a near-unique identifier column (unique_ratio~1.0) with no predictive value.",
            "expected_impact": "high — removes a non-informative identifier",
            "priority_rank": 11,
            "params": {"reason": "high_cardinality_identifier"},
            "source": "rule_based",
            "confidence": 0.95,
        },
        {
            "id": "binning_tenure_months",
            "type": "binning",
            "target_columns": ["tenure_months"],
            "reasoning": "'tenure_months' is a reasonable candidate for quantile binning as an alternative representation.",
            "expected_impact": "low — adds a binned tenure representation",
            "priority_rank": 12,
            "params": {"strategy": "quantile", "n_bins": 4},
            "source": "rule_based",
            "confidence": 0.5,
        },
        {
            "id": "interaction_age_tenure",
            "type": "interaction",
            "target_columns": ["age", "tenure_months"],
            "reasoning": "'age' and 'tenure_months' both rank highly in feature importance and aren't strongly correlated — candidate interaction term.",
            "expected_impact": "low — adds one interaction feature",
            "priority_rank": 13,
            "params": {"operation": "multiply", "new_column": "age_x_tenure_months"},
            "source": "rule_based",
            "confidence": 0.5,
        },
    ]


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "fake_suggestion_list.json"
    out_path.write_text(json.dumps(build_fake_suggestions(), indent=2))
    print(f"Wrote {out_path}")
