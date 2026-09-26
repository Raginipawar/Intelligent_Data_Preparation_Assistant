# Person 3 — Execution / Transform Engine (Apply Layer)

Takes the user's *selected subset* of Person 2's ranked suggestions, actually
applies them to the raw dataset, resolves conflicts, enforces a feature
budget, and produces the final cleaned dataset + a full transformation log —
the artifact Person 4 (algorithm recommendation) builds on next.

**Naming:** every module under `app/` is prefixed `apply_*`
(`apply_api.py`, `apply_config.py`, `apply_schemas.py`, `apply_pipeline.py`,
`app/jobs/apply_job_queue.py`, `app/jobs/apply_job_record.py`) — same
reasoning Person 2 documented in their README: unambiguous in a diff/IDE tab
that this isn't a copy of Person 1's or Person 2's `main.py`/`config.py`/
`schemas.py`. `get_job_queue()` keeps that exact name/interface so it's a
drop-in match with the other two engines' job queues.

## What's implemented

**Apply engine** (`app/apply/`), one module per suggestion `type`, each a
pure `(df, suggestion) -> (df, action_description)` function:

- **Imputation** (`imputation.py`) — mean/median/mode/constant fill.
- **Encoding** (`encoding.py`) — one-hot (replaces the column with dummies),
  frequency, target (single global fit at apply time — Person 2 already
  decided the strategy via its own CV; degrades to frequency encoding if no
  target column is resolvable, and says so in the log).
- **Scaling** (`scaling.py`) — StandardScaler / RobustScaler.
- **Transform** (`transform.py`) — log1p / Yeo-Johnson.
- **Binning** (`binning.py`) — quantile binning into a new `{col}_binned`
  column (original retained); degrades to a single bin for a column with
  fewer than 2 distinct values rather than erroring.
- **Interaction** (`interaction.py`) — multiplicative interaction terms.
- **Drop redundant** (`drop_redundant.py`) — drops `target_columns`, keeping
  `params.kept_column` if present.

Every numeric-facing module (`imputation` mean/median, `scaling`, `transform`,
`binning`, `interaction`) coerces its input with `pd.to_numeric(errors="coerce")`
rather than assuming clean dtype — real datasets can have a nominally-numeric
column with stray non-numeric entries (Person 1's `mixed_type_flag`); those
become `NaN` in that cell instead of crashing the whole suggestion. This was a
real bug caught by live three-engine integration testing against Person 1's
actual messy sample dataset, not a hypothetical.

**Conflict resolution** (`conflict_resolution.py`) — two rules, run on the
*selected* suggestions before anything is applied, both stage-order-aware
(`app/apply/_stage_order.py`, shared with the orchestrator):
1. Two selected suggestions of the **same type** target the same column
   (e.g. two `scaling` suggestions on `age`, one standard one robust) — the
   lower `priority_rank` (Person 2 ranks 1 = best) wins; the loser is logged
   `skipped_conflict`.
2. A selected **one-hot encoding** suggestion removes its target column
   entirely — any other selected suggestion whose pipeline stage runs *after*
   encoding (scaling, transform, binning, interaction) and also targets that
   column is unresolvable and logged `skipped_conflict`. A suggestion whose
   stage runs *before* encoding (imputation) is correctly left alone —
   impute-then-encode is the standard, valid order. (This distinction was
   also a real bug: an earlier version flagged *any* co-targeting suggestion,
   which wrongly blocked a legitimate impute-then-onehot-encode combination
   — caught the same way, via live integration testing.)

`drop_redundant` is excluded from rule 2 entirely — it runs last in the
pipeline order, so anything else still gets to run first (wasted work, not a
conflict).

**Budget-constrained feature selection** (`feature_selection.py`) — after
every suggestion has been applied, if `feature_budget` is set and exceeded,
trims columns in tiers (highest tier dropped first): interaction-created (3)
→ binning-created (2) → one-hot dummy (1) → never raw/original columns (0).
Within a tier, the lowest-`confidence` suggestion's columns go first.

**Orchestration** (`orchestrator.py`) — applies survivors in Person 2's
documented pipeline order: imputation → encoding → scaling → transform →
binning → interaction → drop_redundant. A single bad suggestion (missing
column, bad params) is caught and logged, never crashes the whole run.

**API + job queue**
- `POST /upload`, `POST /apply`, `GET /status/{job_id}`, `GET /result/{job_id}`,
  `POST /export`, `GET /health`.
- Same shared job-queue *pattern* as Person 1's `person1_engine/app/jobs/queue.py`
  (`get_job_queue()`, in-memory by default, Celery+Redis skeleton behind a
  config flag). Same-interface mirror, not a literal shared import — see
  "Why this engine doesn't import the other two" below.

## Running it

```bash
cd person3_engine
python -m venv venv
venv\Scripts\activate            # or source venv/bin/activate on Linux/macOS
pip install -r requirements.txt
uvicorn app.apply_api:app --reload --port 8002
```

Run the test suite (46 tests: every apply/* module in isolation, conflict
resolution, budget trimming, the full orchestrator, and the live API flow —
all using synthetic fixtures, zero dependency on Person 1's or Person 2's
engines running):

```bash
set PYTHONPATH=.   # or: export PYTHONPATH=. on Linux/macOS
pytest tests/ -v
```

## API walkthrough (curl)

**Standalone** (no other engine needed — own /upload + inline suggestions):

```bash
python sample_data/fake_dataset.py            # writes sample_data/fake_dataset.csv
python sample_data/fake_suggestion_list.py     # writes sample_data/fake_suggestion_list.json

curl -X POST http://localhost:8002/upload -F "file=@sample_data/fake_dataset.csv"
# -> {"dataset_id": "...", ...}

curl -X POST http://localhost:8002/apply \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"<dataset_id>\", \"selected_suggestion_ids\": [\"imputation_age\", \"encoding_contract\"], \"suggestions\": $(cat sample_data/fake_suggestion_list.json)}"
# -> {"job_id": "...", "dataset_id": "...", "status": "pending"}

curl http://localhost:8002/status/<job_id>
curl http://localhost:8002/result/<job_id>

curl -X POST http://localhost:8002/export -H "Content-Type: application/json" \
  -d "{\"apply_job_id\": \"<job_id>\", \"format\": \"csv\"}" -o cleaned.csv
```

**Integrated with Person 1 + Person 2** (all three running, co-located storage):

```bash
# 1. Person 1: upload + analyze
curl -X POST http://localhost:8000/upload -F "file=@sample.csv"          # -> dataset_id
curl -X POST "http://localhost:8000/analyze?dataset_id=<dataset_id>"     # -> job_id (poll /status)

# 2. Person 2: suggest
curl -X POST http://localhost:8001/suggest -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"<dataset_id>\", \"source_job_id\": \"<person1_job_id>\"}"  # -> job_id (poll /status)

# 3. Person 3: apply — dataset_id looked up from Person 1's storage, suggestions
#    looked up from Person 2's storage. Only IDs need to be passed.
curl -X POST http://localhost:8002/apply -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"<dataset_id>\", \"source_job_id\": \"<person2_job_id>\", \"selected_suggestion_ids\": [...], \"feature_budget\": 20}"
```

`POST /apply`'s body (`app/apply_schemas.py::ApplyRequest`) also accepts an
optional `target_column` — the dataset's label column, if known (e.g. Person
1's `target_detection.suggested_target`). It's only consulted for `encoding`
suggestions with `method: "target"`; without it, target encoding always
degrades to frequency encoding rather than failing.

## Why this engine doesn't import the other two

All three engines define their own top-level `app` package — a literal
`from person1_engine.app.schemas import ...` (or Person 2's `app`) risks a
namespace collision the moment two engines run in the same process/test
session (confirmed directly while integration-testing Person 1 → Person 2
earlier in this project). So instead:

- Suggestions are consumed via `app/apply_schemas.py::SuggestionIn` — a
  deliberately tolerant mirror (`extra="allow"`, `.get()`-style reads in every
  apply/* module) of Person 2's `Suggestion` contract.
- Cross-engine *files* are only ever touched through `app/dataset_client.py`
  (raw dataset, from Person 1's storage) and `app/suggestion_client.py`
  (suggestion list, from Person 2's storage) — both resolve inline data first,
  then local storage, then a live HTTP call, exactly mirroring Person 2's
  `health_report_client.py` pattern.
- This engine **only ever writes to its own `storage/`** (`datasets/` for its
  own `/upload`, `applied/` for processed datasets + reports, `exports/` for
  downloadable files, `jobs/` for job bookkeeping) — never into Person 1's or
  Person 2's storage.

## Contract notes for Person 4

`POST /apply`'s response (`app/apply_schemas.py::ApplyResult`) is what Person
4's algorithm recommendation engine consumes next:

```json
{
  "dataset_id": "string",
  "apply_job_id": "string",
  "source_job_id": "string or null",
  "status": "success",
  "applied_suggestions": ["string"],
  "skipped_suggestions": [{"suggestion_id": "...", "type": "...", "target_columns": ["..."], "reasoning": "...", "status": "skipped_conflict|skipped_not_selected|skipped_missing_column|skipped_error"}],
  "transformation_log": [{"order": 1, "suggestion_id": "...", "type": "...", "target_columns": ["..."], "action": "...", "reasoning": "...", "status": "applied|budget_drop|skipped_conflict|..."}],
  "final_columns": ["string"],
  "n_rows": 0,
  "n_columns": 0,
  "meta": {"generated_at": "...", "engine_version": "1.0.0", "processing_time_seconds": 0.0}
}
```

The actual cleaned dataset is fetched via `POST /export` (not embedded in the
JSON result — datasets can be large); Person 4 needs it to compute its
meta-features (size, dimensionality, class balance, feature types). `POST
/export` returns the file directly (`Content-Type: text/csv` or
`application/zip`), matching the original upload format by default
(`"format": "auto"`).

**Do not rename `applied_suggestions`, `transformation_log`, `final_columns`,
or their field names without telling the team.**

## File structure

```
person3_engine/
├── app/
│   ├── apply_api.py               # FastAPI: /upload /apply /status /result /export /health
│   ├── apply_pipeline.py          # job-queue entry point: resolve inputs -> orchestrator -> persist
│   ├── apply_config.py
│   ├── apply_schemas.py           # SuggestionIn (tolerant inbound mirror) + ApplyRequest/ApplyResult contract
│   ├── dataset_client.py          # resolves the raw DataFrame (own storage -> Person 1's storage)
│   ├── suggestion_client.py       # resolves the suggestion list (inline -> Person 2's storage/API)
│   ├── export.py                  # writes the processed dataset out as CSV/ZIP
│   ├── jobs/
│   │   ├── apply_job_queue.py     # same shared job-queue pattern as Person 1/2 (own instance)
│   │   └── apply_job_record.py
│   └── apply/
│       ├── imputation.py, encoding.py, scaling.py, transform.py,
│       │   binning.py, interaction.py, drop_redundant.py   # one module per suggestion type
│       ├── conflict_resolution.py
│       ├── feature_selection.py   # budget-constrained trimming
│       ├── _stage_order.py        # pipeline stage order, shared by orchestrator + conflict_resolution
│       └── orchestrator.py        # glues every apply/* module into one pipeline run
├── sample_data/
│   ├── fake_dataset.py            # synthetic messy customer-churn DataFrame
│   └── fake_suggestion_list.py    # synthetic Suggestion List covering all 7 types + a deliberate conflict
├── tests/                         # 46 tests, all passing
└── requirements.txt
```
