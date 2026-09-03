"""
Generates a deliberately messy customer-churn-style dataset to demo/test
the engine against: missing values, mixed-type columns, outliers,
duplicates, a mix of numeric/categorical/datetime/boolean/free-text columns,
and an obvious binary target column.

Run: python sample_data/generate_sample.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 1200

tenure_months = rng.integers(0, 72, n).astype(float)
monthly_charges = rng.normal(65, 20, n).round(2)
monthly_charges[monthly_charges < 10] = 10

# Inject some extreme outliers
outlier_idx = rng.choice(n, 15, replace=False)
monthly_charges[outlier_idx] *= rng.uniform(4, 8, len(outlier_idx))

total_charges = (tenure_months * monthly_charges * rng.uniform(0.9, 1.1, n)).round(2)

contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20])
internet_service = rng.choice(["DSL", "Fiber optic", "No"], n, p=[0.35, 0.45, 0.20])
gender = rng.choice(["Male", "Female"], n)
senior_citizen = rng.choice([0, 1], n, p=[0.84, 0.16])
paperless_billing = rng.choice(["Yes", "No"], n, p=[0.6, 0.4])

signup_date = pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 1500, n), unit="D")

customer_id = [f"CUST-{i:06d}" for i in range(n)]

notes = rng.choice(
    [
        "Called about billing issue, resolved same day.",
        "",
        "Requested upgrade to fiber, scheduled for next week.",
        "Complained about service outage in the area.",
        None,
        "Long-time customer, referred two friends this year.",
    ],
    n,
)

# churn depends (noisily) on tenure, contract type, monthly charges -> gives the
# surrogate model something real to find
churn_score = (
    -0.05 * tenure_months
    + 0.02 * monthly_charges
    + np.where(contract == "Month-to-month", 2.0, 0.0)
    + rng.normal(0, 1.5, n)
)
churned = (churn_score > np.percentile(churn_score, 73)).astype(int)
churned = np.where(churned == 1, "Yes", "No")

df = pd.DataFrame(
    {
        "customer_id": customer_id,
        "gender": gender,
        "senior_citizen": senior_citizen,
        "tenure_months": tenure_months,
        "monthly_charges": monthly_charges,
        "total_charges": total_charges.astype(object),  # will inject mixed-type below
        "contract": contract,
        "internet_service": internet_service,
        "paperless_billing": paperless_billing,
        "signup_date": signup_date.astype(str),
        "support_notes": notes,
        "churned": churned,
    }
)

# --- Inject messiness ---

# 1. Missing values scattered across several columns
for col, frac in [("total_charges", 0.04), ("internet_service", 0.02), ("monthly_charges", 0.01), ("support_notes", 0.35)]:
    mask = rng.random(n) < frac
    df.loc[mask, col] = np.nan

# 2. Mixed-type column: total_charges has some stray non-numeric strings (classic messy-CSV symptom)
mixed_idx = rng.choice(df.index[df["total_charges"].notna()], 10, replace=False)
df.loc[mixed_idx, "total_charges"] = " "

# 3. Exact duplicate rows
dup_rows = df.sample(20, random_state=1)
df = pd.concat([df, dup_rows], ignore_index=True)

# 4. A few malformed rows for the CSV writer to choke on realistically:
# we simulate this at write-time by appending raw broken lines.

df.to_csv("sample_data/customer_churn_messy.csv", index=False)

with open("sample_data/customer_churn_messy.csv", "a") as f:
    # too MANY fields for the header -> genuinely malformed / unparseable row
    f.write("CUST-999999,Male,0,12,55.5,600,Two year,DSL,No,2022-01-01,extra,field,overflow,Yes\n")

print(f"Wrote sample_data/customer_churn_messy.csv with {len(df)} rows (+1 malformed line appended)")
