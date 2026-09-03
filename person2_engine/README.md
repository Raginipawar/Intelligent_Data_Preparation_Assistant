# Person 2 — Preprocessing & Feature Engineering Suggestion Engine

Consumes Person 1's **Dataset Health Report** and turns it into a ranked,
reasoned **Suggestion List** — the contract Person 3's apply/execute layer
consumes next.

**Naming:** every module under `app/` is prefixed `suggestion_*`
(`suggestion_api.py`, `suggestion_config.py`, `suggestion_schemas.py`,
`suggestion_pipeline.py`, `app/jobs/suggestion_job_queue.py`,
`app/jobs/suggestion_job_record.py`) so it's unambiguous at a glance — in a
file tree, a diff, or an IDE tab — that this is Person 2's own code, not a
copy of `person1_engine`'s `main.py`/`config.py`/`schemas.py`. The one
deliberate exception is the `get_job_queue()` *function name and interface*
inside `suggestion_job_queue.py`, which intentionally matches Person 1's — see
"Why this engine doesn't import Person 1's code" below for why that specific
piece stays interface-compatible.

## What's implemented

**Rule engine** (`app/suggestions/`), each suggestion carrying a plain-language
`reasoning` string tied to the actual statistic that triggered it:

- **Imputation** (`missingness_rules.py`) — median for skewed numeric columns,
  mean for symmetric ones, mode for lightly-missing categoricals, an explicit
  `"missing"` category for heavily-missing categoricals (the gap itself may be
  informative), boolean mode-fill. Cross-references Person 1's co-missingness
  (Jaccard-overlap) pairs to flag likely MNAR patterns.
- **Encoding** (`encoding_rules.py`) — one-hot for low-cardinality categoricals,
  cross-validated target encoding when a target is detected and cardinality is
  too high for one-hot, frequency encoding otherwise.
- **Scaling** (`scaling_rules.py`) — RobustScaler for numeric columns Person 1's
  Isolation Forest flagged as outlier-involved, StandardScaler otherwise.
- **Transform** (`transform_rules.py`) — log1p for skewed non-negative columns,
  Yeo-Johnson for skewed columns containing negatives.
- **Redundancy** (`redundancy.py`) — two independent signals, both surfaced as
  `drop_redundant`:
  - Correlated-feature clustering via a real minimum spanning tree over
    `1 - |correlation|` (`_graph_utils.py`, Kruskal's algorithm + union-find,
    zero extra dependencies), cut at a correlation threshold; the cluster
    member with the highest LightGBM feature importance (Person 1's surrogate
    signal) is kept, the rest are suggested for dropping.
  - Near-unique "identifier" columns, using Person 1's strict
    `high_cardinality` flag (unique_ratio ≥ 0.9 and > 20 uniques) — these are
    routed here instead of to `encoding_rules.py`, which explicitly skips them.
- **Binning** (`binning_rules.py`) — quantile binning as an alternative to a
  transform for heavily-skewed columns with moderate cardinality.
- **Interaction** (`interaction_rules.py`) — multiplicative interaction-term
  candidates among Person 1's top-LightGBM-importance columns that aren't
  already strongly correlated with each other.

**AutoML enrichment** (`automl_enrichment.py`, optional, off by default install)
— uses AutoGluon's `AutoMLPipelineFeatureGenerator` (not a full
`TabularPredictor.fit()`) to independently corroborate the rule-based
suggestions above, mirroring Person 1's "primary method + comparison baseline"
philosophy (Isolation Forest + naive distance baseline). auto-sklearn has no
Windows wheels and a real search takes minutes, so it's honestly reported as
skipped with why, rather than faked. **Neither library is a hard dependency —
the core rule engine above works standalone and is what actually drives the
suggestions.**

**API + job queue**
- `POST /suggest`, `GET /status/{job_id}`, `GET /result/{job_id}`, `GET /health`
  — same polling shape as Person 1's `/analyze` flow.
- Same shared job-queue *pattern* as Person 1's `person1_engine/app/jobs/queue.py`
  (`get_job_queue()`, in-memory by default, Celery+Redis skeleton behind a
  config flag). This is a same-interface mirror, not a literal shared import —
  see "Why this engine doesn't import Person 1's code" below.

## Running it

```bash
cd person2_engine
python -m venv venv
venv\Scripts\activate            # or source venv/bin/activate on Linux/macOS
pip install -r requirements.txt
uvicorn app.suggestion_api:app --reload --port 8001
```

Run the test suite (37 tests: every rule module in isolation, the full
orchestration pipeline, and the live API flow — all using a synthetic health
report, zero dependency on Person 1's engine running):

```bash
set PYTHONPATH=.   # or: export PYTHONPATH=. on Linux/macOS
pytest tests/ -v
```

## API walkthrough (curl)

**Standalone** (no Person 1 engine needed — inline health report):

```bash
python sample_data/fake_health_report.py     # writes sample_data/fake_health_report.json

curl -X POST http://localhost:8001/suggest \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"demo-1\", \"health_report\": $(cat sample_data/fake_health_report.json)}"
# -> {"job_id": "...", "dataset_id": "demo-1", "status": "pending"}

curl http://localhost:8001/status/<job_id>
curl http://localhost:8001/result/<job_id>
```

**Integrated with Person 1** (both engines running, co-located storage):

```bash
# 1. Upload + analyze on Person 1's engine (port 8000)
curl -X POST http://localhost:8000/upload -F "file=@sample.csv"          # -> dataset_id
curl -X POST "http://localhost:8000/analyze?dataset_id=<dataset_id>"     # -> job_id
curl http://localhost:8000/status/<job_id>                               # poll until success

# 2. Hand both IDs to Person 2's engine (port 8001) — it fetches the report itself
curl -X POST http://localhost:8001/suggest \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"<dataset_id>\", \"source_job_id\": \"<job_id>\"}"
```

`source_job_id` is Person 1's `/analyze` job id — this engine reads
`../person1_engine/storage/reports/<source_job_id>.json` directly (both
engines assumed co-located under the same repo root), or fetches it live over
HTTP if `PERSON1_API_BASE_URL` is set. Neither path is required — `health_report`
inline always works and keeps this engine fully decoupled.

## Why this engine doesn't import Person 1's code

Both engines define their own top-level `app` package. A literal
`from person1_engine.app.schemas import DatasetHealthReport` risks a namespace
collision the moment both run in the same process/test session, and creates a
hard coupling neither engine should need during independent development. So
instead:

- Core suggestions are derived **entirely from the health report JSON**
  (`app/suggestion_schemas.py::HealthReportIn` is a deliberately tolerant mirror — most
  fields optional, `extra="allow"` — and the rule modules read via `.get()`
  regardless, so a minor field rename on Person 1's side degrades gracefully
  instead of hard-crashing this engine).
- The only place this engine touches Person 1's *files* at all is the optional
  convenience lookup in `app/health_report_client.py` (by `dataset_id`/
  `source_job_id`), and the optional raw-dataset read for AutoGluon enrichment.
  Both degrade to "unavailable, here's why" rather than failing the request.
- This engine **only ever writes to its own `storage/`** — never into
  `person1_engine/storage/` — so there's no file-level write conflict between
  engines, and none with whatever Person 3/4 build alongside this.

## Contract notes for Person 3 (apply/execute layer)

`POST /suggest`'s response (`app/suggestion_schemas.py::SuggestionList`) mostly matches
the project spec's schema, plus one addition your `/apply` step will want:

```json
{
  "dataset_id": "string",
  "source_job_id": "string or null",
  "job_id": "string",
  "status": "success",
  "suggestions": [
    {
      "id": "string",                 
      "type": "imputation | encoding | scaling | transform | drop_redundant | binning | interaction",
      "target_columns": ["string"],
      "reasoning": "string",
      "expected_impact": "string",
      "priority_rank": 1,
      "params": { "...": "concrete, type-specific values — see below" },
      "source": "rule_based | rule_based+autogluon",
      "confidence": 0.0
    }
  ],
  "automl_enrichment": { "autogluon": {"...": "..."}, "auto_sklearn": {"...": "..."} },
  "meta": { "generated_at": "...", "engine_version": "1.0.0", "processing_time_seconds": 0.0 }
}
```

**`params` is additive beyond the spec's minimal schema** — `type` alone tells
you the category, but you need concrete values to actually execute a
suggestion. Shape per `type`:

| type | params |
|---|---|
| `imputation` | `{"strategy": "mean"\|"median"\|"mode"\|"constant", "fill_value"?: "..."}` |
| `encoding` | `{"method": "onehot"\|"frequency"\|"target", "smoothing"?: "cv_smoothed"}` |
| `scaling` | `{"method": "standard"\|"robust"}` |
| `transform` | `{"function": "log1p"\|"yeo_johnson"}` |
| `drop_redundant` | `{"reason": "correlated_redundancy"\|"high_cardinality_identifier", "cluster"?: [...], "kept_column"?: "..."}` |
| `binning` | `{"strategy": "quantile", "n_bins": 5}` |
| `interaction` | `{"operation": "multiply", "new_column": "a_x_b"}` |

`id`s are stable, human-readable slugs (e.g. `imputation_monthly_charges`,
`drop_redundant_customer_id`) — safe to display in a UI's toggle list and to
echo back in your `applied_suggestions`/`skipped_suggestions` lists per the
spec's `/apply` contract. Per the spec's suggested apply order (imputation →
encoding → scaling → transforms → drops), note `drop_redundant`'s
`target_columns` lists the columns to **drop**, not keep — the survivor is in
`params.kept_column` when applicable.

**Do not rename `type`, `target_columns`, or `params` keys here without
telling the team** — this is the contract Person 3 deserializes.

## File structure

```
person2_engine/
├── app/
│   ├── suggestion_api.py             # FastAPI: /suggest /status /result /health
│   ├── suggestion_pipeline.py        # orchestrates input resolution -> suggestion engine -> persist
│   ├── suggestion_config.py
│   ├── suggestion_schemas.py         # HealthReportIn (tolerant inbound mirror) + Suggestion List contract
│   ├── health_report_client.py       # resolves health_report + optional raw dataset (inline/disk/HTTP)
│   ├── jobs/
│   │   ├── suggestion_job_queue.py   # same shared job-queue pattern as Person 1 (own instance)
│   │   └── suggestion_job_record.py
│   └── suggestions/
│       ├── _graph_utils.py           # union-find + Kruskal's MST (no extra dependency)
│       ├── missingness_rules.py      # imputation
│       ├── encoding_rules.py
│       ├── scaling_rules.py
│       ├── transform_rules.py
│       ├── redundancy.py             # drop_redundant: correlated clusters + identifier columns
│       ├── binning_rules.py
│       ├── interaction_rules.py
│       ├── automl_enrichment.py      # optional AutoGluon/auto-sklearn corroboration
│       └── suggestion_builder.py     # orchestrator: runs every rule module, ranks, assigns ids
├── sample_data/fake_health_report.py # synthetic health report for standalone dev/test/demo
├── tests/                            # 37 tests, all passing
└── requirements.txt
```
