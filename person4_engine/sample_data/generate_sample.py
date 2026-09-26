"""
generate_sample.py — Generates synthetic sample dataset for testing person4_engine standalone.
"""
from pathlib import Path
import numpy as np
import pandas as pd

SAMPLE_DIR = Path(__file__).parent
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def generate():
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "age": np.random.randint(18, 70, size=n),
        "income": np.random.normal(50000, 15000, size=n),
        "tenure_months": np.random.exponential(scale=12, size=n),
        "credit_score": np.random.randint(300, 850, size=n),
        "contract_type": np.random.choice(["month-to-month", "one-year", "two-year"], size=n, p=[0.6, 0.25, 0.15]),
        "paperless_billing": np.random.choice([True, False], size=n),
        "churn": np.random.choice([0, 1], size=n, p=[0.75, 0.25])
    })

    out_file = SAMPLE_DIR / "sample_churn.csv"
    df.to_csv(out_file, index=False)
    print(f"Generated sample dataset: {out_file} ({len(df)} rows, {len(df.columns)} cols)")


if __name__ == "__main__":
    generate()
