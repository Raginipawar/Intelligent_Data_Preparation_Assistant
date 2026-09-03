# Person 1 — Data Ingestion & Deep Analysis (Profiling Engine)

Turns a raw, messy CSV/ZIP upload into a structured **Dataset Health Report** —
the JSON contract that Persons 2, 3, and 4 build on top of.

## What's implemented

**Ingestion**
- CSV and ZIP upload, with auto-detection of single CSV / multiple CSVs (joined
  on a shared key if one exists, else largest table treated as primary) /
  CSV + supporting non-CSV files
- Encoding detection (`charset-normalizer`), delimiter detection (`csv.Sniffer`
  + frequency fallback), malformed-row tolerance (parsing continues, bad rows
  are counted and reported, not silently dropped without a trace)
- Smart dtype inference beyond pandas defaults: `numeric_int`, `numeric_float`,
  `categorical`, `datetime`, `boolean`, `text_freeform`, plus a `mixed_type_flag`
  for columns with stray non-numeric values in an otherwise numeric column

**Statistical deep analysis**
- Missing value analysis (per-column %, plus co-missingness pairs via Jaccard
  overlap of null-masks)
- Distribution analysis: mean/std/min/max/median/skewness/kurtosis + histogram
  per numeric column
- Cardinality analysis: unique counts, unique ratio, high-cardinality flag, top
  values
- Pearson correlation matrix + extracted high-correlation pairs
- Target/label detection heuristics (name keywords, cardinality, position,
  missingness — full transparent scoring, not just a silent guess)
- Exact duplicate row detection via row hashing

**Outlier & anomaly detection**
- Isolation Forest (primary) with column-level "involvement" scoring
  (which columns drive each flagged row's anomaly, via z-score contribution)
- Naive Euclidean-distance-from-centroid baseline for comparison
- Agreement rate between the two methods

**Quick Signal Layer**
- Fast, untuned LightGBM fit on the detected target for rough feature
  importance — a head start for Person 2, explicitly labeled as "rough" in
  the output so it's never mistaken for a real model

**API + job queue**
- `POST /upload` and `POST /analyze` (FastAPI)
- A shared, swappable job-queue abstraction (`app/jobs/queue.py`) — in-memory
  by default (zero setup), with a Celery+Redis skeleton behind a config flag
  for when the team wants real distributed workers. **Persons 2-4: use this
  same `get_job_queue()` pattern for `/suggest`, `/apply`, `/export`, and
  `/recommend`** so all four stages share one concurrency model.

## Running it

```bash
cd person1_engine
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

Generate the synthetic messy demo dataset (missing values, mixed-type
column, injected outliers, duplicate rows, a malformed CSV line):

```bash
python3 sample_data/generate_sample.py
```

Run the test suite (21 tests: ingestion edge cases, dtype inference, every
analysis module, outlier detection, the surrogate model, the pydantic
contract, and the full live API flow):

```bash
PYTHONPATH=. pytest tests/ -v
```

## API walkthrough (curl)

```bash
# 1. Upload — fast, synchronous. Returns dataset_id + basic schema immediately.
curl -X POST http://localhost:8000/upload \
  -F "file=@sample_data/customer_churn_messy.csv"
# -> {"dataset_id": "...", "ingestion": {...}, "schema": {...}}

# 2. Analyze — kicks off the heavy stats/ML pass in the background.
curl -X POST "http://localhost:8000/analyze?dataset_id=<dataset_id>"
# -> {"job_id": "...", "dataset_id": "...", "status": "pending"}

# 3. Poll status until it flips to "success" (or "failed").
curl http://localhost:8000/status/<job_id>

# 4. Fetch the finished Dataset Health Report.
curl http://localhost:8000/result/<job_id>
```

## The contract: Dataset Health Report

Defined in `app/schemas.py::DatasetHealthReport` — this is what Person 2's
`/suggest` deserializes. Top-level keys: `ingestion`, `schema`, `missingness`,
`distributions`, `cardinality`, `correlation`, `target_detection`,
`duplicates`, `outliers`, `feature_importance_signal`, `meta`.

**Do not rename fields here without telling the team** — Person 2 will be
importing `DatasetHealthReport` directly to deserialize `/result`'s response.

## Design notes / things Persons 2-4 should know

- `/upload` does ingestion + dtype inference only (fast, synchronous). All the
  expensive statistical/ML work is in `/analyze`, which runs through the job
  queue. Don't block on `/upload` expecting the full report — poll `/analyze`'s
  job instead.
- The surrogate LightGBM signal is deliberately rough (50 boosting rounds, no
  CV, no leakage guarding beyond dropping free-text columns). It exists to give
  Person 2 a head start on feature importance, not to replace Person 2's own
  preprocessing-aware modeling.
- If no target column can be confidently detected, or the dataset is too small
  (<30 rows) or has no numeric columns, the outlier/surrogate sections degrade
  gracefully (`null` / `"ran": false` with a `note` explaining why) rather than
  erroring out — check for that before assuming those sections are populated.
- ydata-profiling is listed in the project's tools but is NOT a hard dependency
  here: the custom analysis modules already cover everything in the required
  spec (missingness, distributions, cardinality, correlation, duplicates,
  target detection) with full control over the JSON contract. If the team
  wants an additional ydata-profiling HTML report as a bonus artifact, it can
  be bolted on as an optional step without touching the core contract.

## File structure

```
person1_engine/
├── app/
│   ├── main.py                    # FastAPI app: /upload /analyze /status /result
│   ├── pipeline.py                # orchestrates ingestion -> analysis -> report
│   ├── config.py
│   ├── schemas.py                 # THE Dataset Health Report contract
│   ├── jobs/
│   │   ├── queue.py                # shared job-queue pattern (in-memory + Celery skeleton)
│   │   └── models.py
│   ├── ingestion/
│   │   ├── loader.py                # CSV/ZIP parsing, encoding/delimiter detection
│   │   └── dtype_inference.py       # smart dtype classification
│   ├── analysis/
│   │   ├── missingness.py, distributions.py, cardinality.py,
│   │   └── correlation.py, target_detection.py
│   ├── outliers/
│   │   ├── isolation_forest.py
│   │   └── distance_baseline.py
│   └── surrogate/
│       └── lightgbm_signal.py
├── sample_data/generate_sample.py   # synthetic messy dataset generator
├── tests/                           # 21 tests, all passing
└── requirements.txt
```
