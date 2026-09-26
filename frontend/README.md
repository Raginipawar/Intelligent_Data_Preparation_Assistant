# DataPrep AI — Frontend

React + Vite single-page app that walks a user through the full pipeline:
**Upload → Analyze → Suggest → Apply & Export → Recommend**. Owned separately
from the 4-person engine split (per the project spec), and calls each engine's
API directly from the browser.

## Screens

| Route | Calls | Status |
|---|---|---|
| `/` Home (marketing) | — | static |
| `/workspace` Upload | Person 1's `POST /upload` | live |
| `/workspace/analysis` Dataset Health Report | Person 1's `POST /analyze` → poll → `GET /result` | live |
| `/workspace/suggestions` Suggestions | Person 2's `POST /suggest` → poll → `GET /result` | live |
| `/workspace/apply` Apply & Export | Person 3's `POST /apply` → poll → `GET /result`, `POST /export` | live |
| `/workspace/recommend` Recommendations | Person 4's `POST /recommend` → poll → `GET /result` | live |

`/` is the public-facing landing page (hero, how-it-works, deliverables, about)
— the tool itself lives under `/workspace/*`, reachable via the nav's "Get
started" button. A `StepperNav` ties the five workspace screens together; a
step is only clickable once the previous step's data exists (tracked in
`PipelineContext`). Uses `BrowserRouter` (real paths, not `#/hash` routes) —
this matters because the homepage's in-page anchor links (`#how-it-works`
etc.) would otherwise collide with hash-based routing.

All four screens were verified against a real running instance of every
engine (a live curl walkthrough through all four stages, not just against
each engine's documented contract) — see "Two backend bugs found along the
way" below for what that caught.

## Running it

```bash
# terminal 1
cd person1_engine && uvicorn app.main:app --reload --port 8000

# terminal 2
cd person2_engine && uvicorn app.suggestion_api:app --reload --port 8001

# terminal 3
cd person3_engine && uvicorn app.apply_api:app --reload --port 8002

# terminal 4
cd person4_engine && uvicorn app.recommend_api:app --reload --port 8003

# terminal 5
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Every engine got a CORS middleware addition (`allow_origins=["*"]`, local-dev
only) so the Vite dev server can call them directly from the browser — see
each engine's `app/*_api.py` (or `app/main.py` for Person 1).

Ports/URLs are configurable in `.env.development` (`VITE_PERSON1_API_URL`
through `VITE_PERSON4_API_URL`). For a one-off override without touching the
tracked file, create `.env.development.local` (gitignored).

**Recommend can be slow.** Person 4's benchmark step runs real 5-fold
cross-validation on the top candidates — on a still-messy dataset (wide,
high-cardinality/free-text columns left unencoded) this took ~50s in local
testing. The frontend's poll timeout for this stage is set to 3 minutes
accordingly (`person4Api.js`); it's not a hang.

## Mock fallback (frontend-only dev)

`src/mocks/person3Mock.js` / `person4Mock.js` return data shaped exactly like
the real engines' responses (confirmed against live output, not just their
READMEs) — set `VITE_MOCK_PERSON3` / `VITE_MOCK_PERSON4` to `true` in
`.env.development` to use them instead of the real engines (e.g. if you only
want to work on Apply/Recommend UI without running the Python side). Nothing
in `src/pages/` or `src/components/` needs to change either way — they only
ever import from `person3Api.js` / `person4Api.js`, which own the switch.

## Two backend bugs found along the way

Wiring the frontend to the real engines (rather than just their READMEs)
surfaced two bugs, both fixed in place:

1. **Person 3 was reading Person 2's storage from the wrong path.**
   `apply_config.py` defaulted `PERSON2_STORAGE_DIR` to `person3_engine/../storage`
   (a comment claimed "Person 2's engine lives at the repo root" — it doesn't;
   it's `person2_engine/`, a sibling folder, same as every other engine). Every
   `/apply` call with a `source_job_id` failed with "No suggestion list
   available" until this was corrected to `person3_engine/../person2_engine/storage`.
2. **Person 4's `mean_absolute_correlation` could be `NaN`**, which crashes
   FastAPI's default JSON response (Starlette's `JSONResponse` uses
   `allow_nan=False`) — any dataset with a constant numeric column (undefined
   correlation) would 500 on `/result`. `meta_features.py` now falls back to
   the documented `0.0` default when the computed mean is `NaN`, same as it
   already did for the "fewer than 2 numeric columns" case.

Also fixed a cosmetic issue in Person 3's imputation action strings — numpy
2.x's `repr()` was leaking through as `"...with median (np.float64(65.04))"`;
now shows `65.04`.

## Architecture

```
src/
├── api/                      # one module per engine — the ONLY place that knows
│   ├── client.js             #   about base URLs / fetch / job polling
│   ├── person1Api.js         # upload, analyze (+ poll)
│   ├── person2Api.js         # suggest (+ poll)
│   ├── person3Api.js         # apply (+ poll), export — mock/real switch (VITE_MOCK_PERSON3)
│   └── person4Api.js         # recommend (+ poll) — mock/real switch (VITE_MOCK_PERSON4)
├── mocks/
│   ├── person3Mock.js        # apply/export contract, derived from real selected suggestions
│   └── person4Mock.js        # recommend contract, matching the real engine's shape
├── utils/
│   ├── text.js                # stripLongDashes() — see "No em-dashes" below
│   └── stageOrder.js          # Person 3's real apply pipeline order, shared by the mock
├── context/
│   └── PipelineContext.jsx   # single source of truth for the wizard's state
├── components/
│   ├── StepperNav.jsx, FileDropzone.jsx, SuggestionCard.jsx, ...
│   ├── effects/                # React Bits integrations (Particles, GradualBlur, BorderGlow,
│   │                            SplashCursor — homepage only; see HomePage.jsx)
│   └── charts/                # dataviz-skill-compliant chart components (see below)
└── pages/
    ├── UploadPage.jsx, AnalysisPage.jsx, SuggestionsPage.jsx,
    └── ApplyExportPage.jsx, RecommendationsPage.jsx
```

**State flow:** each page reads/writes `PipelineContext` (`usePipeline()`).
Later steps depend on earlier ones — Suggestions needs Person 1's
`analysisJobId` as `source_job_id` for `/suggest`; Apply needs Person 2's
`suggestionJobId` as `source_job_id` for `/apply` (plus the detected
`target_detection.suggested_target`, used for target-encoding suggestions);
Recommend needs Person 3's `applyResult.apply_job_id` plus that same target
column. Nothing is persisted beyond the session — refreshing restarts the
wizard at Upload.

**No em-dashes.** `src/utils/text.js`'s `stripLongDashes()` runs on every
piece of dynamic reasoning/note/action text rendered from any engine's
response, since none of the four backends can be guaranteed to stay
em-dash-free at the source — it's a display-layer rule, applied at every call
site that renders backend-generated prose (see `SuggestionCard.jsx`,
`AnalysisPage.jsx`, `ApplyExportPage.jsx`, `RecommendationsPage.jsx`).

**Charts** (`src/components/charts/`) follow the project's dataviz skill:
sequential single-hue blue for magnitude (missingness bars, histograms,
feature importance), a diverging blue↔red scale around a neutral gray
midpoint for the correlation heatmap (polarity, not magnitude), hover
tooltips on every chart, and color values pulled from the skill's validated
reference palette (`chartColors.js`) rather than picked by eye.

## Contract notes / things to know

- Person 2's `/suggest` is looked up by `dataset_id` + `source_job_id`
  (Person 1's `/analyze` job id) — see `person2Api.js`. It resolves the health
  report from Person 1's shared local storage itself; the frontend never
  fetches/forwards the report body. Person 3's `/apply` follows the identical
  pattern one stage later (`source_job_id` = Person 2's suggest job id).
- `SuggestionCard` renders `suggestion.params` per type (imputation strategy,
  encoding method, etc.) — see `person2_engine/README.md`'s contract table if
  a new suggestion type/param shape shows up and a card needs updating.
- Person 3's real apply order is **imputation → encoding → scaling →
  transform → binning → interaction → drop_redundant** (`drop_redundant` runs
  *last*, not third — see `src/utils/stageOrder.js`, which the mock uses so
  its ordering matches the real engine's documented behavior exactly).
- Person 3's `skipped_suggestions[].status` is one of `skipped_conflict` /
  `skipped_not_selected` / `skipped_missing_column` / `skipped_error` —
  `ApplyExportPage.jsx`'s `SKIPPED_LABEL` map turns these into short display
  labels; extend that map if Person 3 adds a new status value.
- Person 4's `recommendations[].reasoning` is an **array** of strings, not one
  string, and `.benchmark` is `null` for any candidate past `top_k_benchmark`
  (only the top-K get a real cross-validated score — the rest are
  meta-learning-only ranks). `RecommendationsPage.jsx` handles both.
