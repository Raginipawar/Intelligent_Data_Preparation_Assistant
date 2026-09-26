"""
fake_dataset.py — builds a small, deterministic, synthetic customer-churn
DataFrame for standalone development/testing of this engine WITHOUT Person 1's
or Person 2's engines running. Same column shape as Person 2's
sample_data/fake_health_report.py (repo root) so the two fixtures pair up
naturally in an integration test:

  - 'tenure_months'      numeric, mildly skewed, no missing
  - 'monthly_charges'    numeric, missing ~8%, roughly symmetric
  - 'total_charges'      numeric, heavily right-skewed, correlated with
                          monthly_charges -> drop_redundant candidate
  - 'age'                numeric, missing ~2%
  - 'contract'            categorical, low cardinality (3) -> one-hot
  - 'signup_channel'      categorical, higher cardinality, missing ~12%
  - 'customer_id'         near-unique identifier -> drop candidate
  - 'is_autopay'          boolean, missing ~4%
  - 'churned'              boolean target

Run directly to write sample_data/fake_dataset.csv:

    python sample_data/fake_dataset.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def build_fake_dataset(n_rows: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    tenure_months = rng.integers(0, 72, size=n_rows)
    monthly_charges = np.round(rng.normal(65, 30, size=n_rows).clip(18, 120), 2)
    # heavily right-skewed, loosely tracking monthly_charges * tenure
    total_charges = np.round(
        monthly_charges * (tenure_months + 1) * rng.uniform(0.8, 1.2, size=n_rows), 2
    )
    age = rng.integers(18, 95, size=n_rows)
    contract = rng.choice(["month-to-month", "one-year", "two-year"], size=n_rows, p=[0.55, 0.28, 0.17])
    signup_channel = rng.choice(
        ["web", "referral", "store", "partner", "phone"], size=n_rows, p=[0.4, 0.2, 0.2, 0.1, 0.1]
    )
    customer_id = [f"CUST-{i:05d}" for i in range(n_rows)]
    is_autopay = rng.choice([True, False], size=n_rows, p=[0.6, 0.4])
    churn_prob = 0.15 + 0.25 * (contract == "month-to-month") - 0.05 * is_autopay
    churned = rng.random(n_rows) < churn_prob

    df = pd.DataFrame(
        {
            "tenure_months": tenure_months,
            "monthly_charges": monthly_charges,
            "total_charges": total_charges,
            "age": age,
            "contract": contract,
            "signup_channel": signup_channel,
            "customer_id": customer_id,
            "is_autopay": is_autopay,
            "churned": churned,
        }
    )

    # Inject missingness matching the fake health report's stated percentages.
    df["is_autopay"] = df["is_autopay"].astype("object")

    def _blank(col: str, frac: float):
        idx = rng.choice(n_rows, size=int(n_rows * frac), replace=False)
        df.loc[idx, col] = np.nan

    _blank("monthly_charges", 0.08)
    _blank("age", 0.02)
    _blank("signup_channel", 0.12)
    _blank("is_autopay", 0.04)

    return df


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "fake_dataset.csv"
    build_fake_dataset().to_csv(out_path, index=False)
    print(f"Wrote {out_path}")
