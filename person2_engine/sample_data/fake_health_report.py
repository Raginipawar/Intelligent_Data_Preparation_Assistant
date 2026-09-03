"""
fake_health_report.py — builds a synthetic, self-consistent Dataset Health
Report (matching Person 1's contract) for standalone development, testing, and
demoing this engine WITHOUT Person 1's engine running. Deliberately shaped to
exercise every rule branch in app/suggestions/*.py:

  - 'tenure_months'      numeric, mildly skewed, no missing
  - 'monthly_charges'    numeric, missing 8%, roughly symmetric
  - 'total_charges'      numeric, heavily right-skewed, correlated with
                          monthly_charges (r=0.93) -> drop_redundant candidate
  - 'age'                numeric, missing 2%, involved in outliers -> robust scaling
  - 'contract'            categorical, low cardinality (3) -> one-hot
  - 'signup_channel'      categorical, higher cardinality (18), missing 12%
  - 'customer_id'         text_freeform, near-unique -> identifier drop
  - 'is_autopay'          boolean, missing 4%
  - 'churned'              the detected target (classification)

Run directly to write sample_data/fake_health_report.json (handy for curling
POST /suggest with `health_report` inline without any other service running):

    python sample_data/fake_health_report.py
"""
from __future__ import annotations

import json
from pathlib import Path


def build_fake_health_report(dataset_id: str = "fake-dataset-001", job_id: str = "fake-job-001") -> dict:
    return {
        "dataset_id": dataset_id,
        "job_id": job_id,
        "status": "success",
        "ingestion": {
            "dataset_id": dataset_id,
            "source_type": "single_csv",
            "primary_file": "customer_churn_fake.csv",
            "supporting_files": [],
            "encoding": "utf-8",
            "encoding_confidence": 1.0,
            "delimiter": ",",
            "n_rows": 5000,
            "n_columns": 9,
            "malformed_rows_skipped": 0,
            "parsing_warnings": [],
        },
        "schema": {
            "columns": [
                {"name": "tenure_months", "inferred_dtype": "numeric_int", "pandas_dtype": "int64", "sample_values": [12, 34, 5], "mixed_type_flag": False},
                {"name": "monthly_charges", "inferred_dtype": "numeric_float", "pandas_dtype": "float64", "sample_values": [55.2, 89.9, 20.1], "mixed_type_flag": False},
                {"name": "total_charges", "inferred_dtype": "numeric_float", "pandas_dtype": "float64", "sample_values": [660.4, 3056.6, 100.5], "mixed_type_flag": True},
                {"name": "age", "inferred_dtype": "numeric_int", "pandas_dtype": "int64", "sample_values": [34, 51, 29], "mixed_type_flag": False},
                {"name": "contract", "inferred_dtype": "categorical", "pandas_dtype": "object", "sample_values": ["month-to-month", "one-year", "two-year"], "mixed_type_flag": False},
                {"name": "signup_channel", "inferred_dtype": "categorical", "pandas_dtype": "object", "sample_values": ["web", "referral", "store"], "mixed_type_flag": False},
                {"name": "customer_id", "inferred_dtype": "text_freeform", "pandas_dtype": "object", "sample_values": ["CUST-00019", "CUST-00020"], "mixed_type_flag": False},
                {"name": "is_autopay", "inferred_dtype": "boolean", "pandas_dtype": "object", "sample_values": [True, False], "mixed_type_flag": False},
                {"name": "churned", "inferred_dtype": "boolean", "pandas_dtype": "object", "sample_values": [True, False], "mixed_type_flag": False},
            ]
        },
        "missingness": {
            "overall_missing_pct": 3.2,
            "columns": {
                "tenure_months": {"missing_count": 0, "missing_pct": 0.0},
                "monthly_charges": {"missing_count": 400, "missing_pct": 8.0},
                "total_charges": {"missing_count": 60, "missing_pct": 1.2},
                "age": {"missing_count": 100, "missing_pct": 2.0},
                "contract": {"missing_count": 0, "missing_pct": 0.0},
                "signup_channel": {"missing_count": 600, "missing_pct": 12.0},
                "customer_id": {"missing_count": 0, "missing_pct": 0.0},
                "is_autopay": {"missing_count": 200, "missing_pct": 4.0},
                "churned": {"missing_count": 0, "missing_pct": 0.0},
            },
            "co_missing_pairs": [
                {"col1": "monthly_charges", "col2": "total_charges", "co_missing_rows": 55, "jaccard": 0.62},
            ],
        },
        "distributions": {
            "columns": {
                "tenure_months": {"count": 5000, "mean": 32.1, "std": 18.4, "min": 0, "max": 72, "median": 30, "skewness": 0.6, "kurtosis": -0.3, "histogram": {"bin_edges": [0, 72], "counts": [5000]}},
                "monthly_charges": {"count": 4600, "mean": 64.8, "std": 30.1, "min": 18.25, "max": 118.75, "median": 70.35, "skewness": -0.2, "kurtosis": -1.1, "histogram": {"bin_edges": [18.25, 118.75], "counts": [4600]}},
                "total_charges": {"count": 4940, "mean": 2280.3, "std": 2265.7, "min": 0.0, "max": 8684.8, "median": 1397.5, "skewness": 3.2, "kurtosis": 12.5, "histogram": {"bin_edges": [0, 8684.8], "counts": [4940]}},
                "age": {"count": 4900, "mean": 41.2, "std": 16.9, "min": 18, "max": 95, "median": 40, "skewness": 0.4, "kurtosis": -0.1, "histogram": {"bin_edges": [18, 95], "counts": [4900]}},
            }
        },
        "cardinality": {
            "columns": {
                "tenure_months": {"n_unique": 73, "unique_ratio": 0.0146, "high_cardinality": False, "top_values": {"1": 120}},
                "monthly_charges": {"n_unique": 1584, "unique_ratio": 0.3168, "high_cardinality": False, "top_values": {}},
                "total_charges": {"n_unique": 4870, "unique_ratio": 0.974, "high_cardinality": False, "top_values": {}},
                "age": {"n_unique": 78, "unique_ratio": 0.0156, "high_cardinality": False, "top_values": {}},
                "contract": {"n_unique": 3, "unique_ratio": 0.0006, "high_cardinality": False, "top_values": {"month-to-month": 2800, "one-year": 1400, "two-year": 800}},
                "signup_channel": {"n_unique": 18, "unique_ratio": 0.0036, "high_cardinality": False, "top_values": {"web": 1800}},
                "customer_id": {"n_unique": 5000, "unique_ratio": 1.0, "high_cardinality": True, "top_values": {}},
                "is_autopay": {"n_unique": 2, "unique_ratio": 0.0004, "high_cardinality": False, "top_values": {"True": 3000, "False": 1800}},
                "churned": {"n_unique": 2, "unique_ratio": 0.0004, "high_cardinality": False, "top_values": {"False": 3650, "True": 1350}},
            }
        },
        "correlation": {
            "method": "pearson",
            "matrix": {
                "tenure_months": {"tenure_months": 1.0, "monthly_charges": 0.05, "total_charges": 0.65, "age": 0.02},
                "monthly_charges": {"tenure_months": 0.05, "monthly_charges": 1.0, "total_charges": 0.93, "age": 0.01},
                "total_charges": {"tenure_months": 0.65, "monthly_charges": 0.93, "total_charges": 1.0, "age": 0.03},
                "age": {"tenure_months": 0.02, "monthly_charges": 0.01, "total_charges": 0.03, "age": 1.0},
            },
            "high_correlation_pairs": [
                {"col1": "monthly_charges", "col2": "total_charges", "corr": 0.93},
            ],
        },
        "target_detection": {
            "suggested_target": "churned",
            "confidence": 0.92,
            "reasoning": "column name 'churned' matches a common target keyword; low-cardinality boolean column",
            "task_type_guess": "classification",
            "candidates": [{"column": "churned", "score": 5.0, "reasoning": "name match + low cardinality"}],
        },
        "duplicates": {"exact_duplicate_rows": 12, "duplicate_pct": 0.24, "duplicate_row_indices": [10, 55]},
        "outliers": {
            "isolation_forest": {
                "contamination": 0.05,
                "dataset_anomaly_rate": 0.05,
                "flagged_row_indices": [3, 88, 205],
                "column_involvement": {"tenure_months": 12, "monthly_charges": 3, "total_charges": 40, "age": 0},
            },
            "distance_baseline": {"method": "euclidean_from_centroid", "threshold": 3.5, "flagged_row_indices": [3, 88]},
            "agreement_rate": 0.7,
            "note": None,
        },
        "feature_importance_signal": {
            "model": "lightgbm",
            "ran": True,
            "target_used": "churned",
            "task_type": "classification",
            "importances": {
                "total_charges": 0.42,
                "tenure_months": 0.28,
                "monthly_charges": 0.15,
                "age": 0.10,
                "contract": 0.05,
            },
            "note": "Rough signal only.",
        },
        "meta": {"generated_at": "2026-01-01T00:00:00+00:00", "engine_version": "1.0.0", "processing_time_seconds": 1.23},
    }


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "fake_health_report.json"
    out_path.write_text(json.dumps(build_fake_health_report(), indent=2))
    print(f"Wrote {out_path}")
