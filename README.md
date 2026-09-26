# DataPrep AI

An intelligent, end-to-end engine that turns raw, messy tabular datasets into clean, model-ready data automatically. Most people working with data spend the majority of their time on preprocessing and feature engineering, often without knowing which transformations actually help, or which ML algorithm suits their data best. DataPrep AI closes that gap by combining automated deep data analysis, ML-driven preprocessing recommendations, and algorithm suggestion into a single guided pipeline.

Instead of relying on rigid rule-based checks ("if column has >40% nulls, impute"), DataPrep AI uses real AutoML libraries AutoGluon and auto-sklearn — to analyze the dataset's actual statistical structure and propose preprocessing and feature engineering steps with reasoning attached to each suggestion. Users review these suggestions, choose what to apply, and get a cleaned dataset back — along with a ranked list of ML algorithms suited to it.

---

## Table of Contents

| Section | Reference |
|---------|-----------|
| [What This Project Delivers](#what-this-project-delivers) | Capabilities and output overview |
| [Project Pipeline](#project-pipeline) | Four-stage system breakdown |
| &emsp;[Stage 1 — Data Ingestion & Deep Analysis](#stage-1--data-ingestion--deep-analysis) | Profiling engine |
| &emsp;[Stage 2 — Preprocessing & Feature Engineering Suggestions](#stage-2--preprocessing--feature-engineering-suggestions) | AutoML-driven recommendation engine |
| &emsp;[Stage 3 — Execution / Transform Engine](#stage-3--execution--transform-engine) | Apply layer |
| &emsp;[Stage 4 — Algorithm Recommendation](#stage-4--algorithm-recommendation) | Meta-learning based model suggestion |
| [How the Stages Work Together](#how-the-stages-work-together) | Combined pipeline flow |
| [Tech Stack](#tech-stack) | Technologies and tools used |
| [Module Overview](#module-overview) | File/component breakdown |
| [How to Run](#how-to-run) | Setup instructions |
| [Team Framework](#team-framework) | Role distribution |
| [Datasets & References](#datasets--references) | Test datasets and research references |
| [Future Scope](#future-scope) | Planned enhancements |

---

## What This Project Delivers

DataPrep AI is a **four-stage AI-driven pipeline** that runs on any uploaded tabular dataset and delivers:

- **Deep Dataset Analysis** — a full statistical health report: missing values, distributions, correlations, cardinality, outliers, duplicates, and a guessed target column.
- **Smart Preprocessing & Feature Engineering Suggestions** — ranked recommendations for imputation, encoding, scaling, transformations, and redundant-feature clustering, each with a reasoning string, not just a black-box output.
- **One-Click Transformation** — apply the chosen suggestions to the dataset and export a clean CSV/ZIP, with a full transformation log.
- **Algorithm Recommendation** — a ranked shortlist of ML algorithms suited to the final dataset, backed by meta-learning and optional live benchmarking.

---

## Project Pipeline

### Stage 1 — Data Ingestion & Deep Analysis

**Owner:** Person 1

**What it does:**
Accepts CSV or ZIP uploads (single CSV, multiple related CSVs, or CSV + supporting files), performs robust parsing and smart dtype inference, then runs a full statistical profile on the dataset.

**What it analyzes:**
- Missing value patterns per column
- Distribution shape — skewness, kurtosis
- Cardinality and high-cardinality flags
- Correlation matrix across numeric features
- Target/label column detection
- Duplicate rows (hashing-based, not brute-force pairwise)
- Outliers/anomalies via Isolation Forest, benchmarked against a naive distance-based baseline

**Why it matters:**
This is the foundation layer — every downstream suggestion depends on an accurate, complete picture of the raw dataset's structure and quality.

**Output:** A structured JSON **Dataset Health Report**.

---

### Stage 2 — Preprocessing & Feature Engineering Suggestions

**Owner:** Person 2

**What it does:**
Consumes the Dataset Health Report and runs AutoGluon / auto-sklearn to determine an appropriate preprocessing pipeline — imputation, encoding, and scaling strategies per column — along with feature engineering suggestions such as transformations, binning, and interaction terms.

**What it detects:**
- Best-fit preprocessing strategy per column (not hardcoded rules)
- Skewed columns needing log/power transforms
- Redundant or highly correlated features, clustered together
- Ranked suggestions, each with a plain-language reasoning string

**Why it matters:**
Segmentation-style zone context isn't relevant here — instead, this layer answers: *"Column `income` is right-skewed (skew = 3.2) and log-transforming it is expected to improve model performance."* Every suggestion is explainable, not a black box.

**Output:** A ranked JSON **Suggestion List**.

---

### Stage 3 — Execution / Transform Engine

**Owner:** Person 3

**What it does:**
Takes the user's selected suggestions and applies them to the dataset — handling feature selection under constraints, resolving conflicts between incompatible transforms, and exporting the final result.

**What it handles:**
- Applying chosen preprocessing/FE steps in the correct order
- Feature subset selection under a budget/limit
- Conflict resolution when two transforms can't both apply to the same column
- Export to CSV or ZIP, matching the original upload format

**Output:** The final **processed dataset** + a **transformation log**.

---

### Stage 4 — Algorithm Recommendation

**Owner:** Person 4

**What it does:**
Takes the final processed dataset's meta-features — size, task type, dimensionality, class balance, feature types — and runs a meta-learning-based recommendation (auto-sklearn's model search / OpenML meta-feature matching) to shortlist and rank suitable ML algorithms.

**What it decides:**

| Output | Description |
|--------|-------------|
| Ranked algorithm list | e.g. XGBoost, Random Forest, Logistic Regression |
| Reasoning per algorithm | Why it fits — data size, feature types, task type |
| Optional benchmark score | Real accuracy/F1/RMSE from quickly fitting top candidates |

**Why it matters:**
Rather than guessing or hardcoding "try Random Forest," this layer grounds its recommendation in how similar datasets have historically performed with different algorithms — and validates it empirically where possible.

**Output:** A ranked JSON **Algorithm Recommendation Report**.

---

## How the Stages Work Together

```
Raw Dataset (CSV / ZIP Upload)
     │
     ├──► Stage 1: Profiling Engine   ──► Dataset Health Report
     │
     ├──► Stage 2: Suggestion Engine  ──► Ranked Suggestion List (with reasoning)
     │
     ├──► Stage 3: Transform Engine   ──► Processed Dataset + Transformation Log
     │
     └──► Stage 4: Recommendation Engine ──► Ranked Algorithm Report
                                                        │
                                            Clean, Model-Ready Dataset + Guidance
```

Each stage exposes its own FastAPI endpoint and consumes the previous stage's JSON output directly — the pipeline is fully callable end-to-end via API calls alone, even before the UI exists.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Profiling | ydata-profiling |
| Preprocessing / Feature Engineering | AutoGluon, auto-sklearn |
| Outlier Detection | scikit-learn (Isolation Forest) |
| Feature Importance | LightGBM |
| Algorithm Recommendation | auto-sklearn model search, OpenML meta-features |
| Backend API | FastAPI |
| Background Jobs | Async background tasks / Celery + Redis |
| Frontend | React (owned separately, outside the 4-person engine split) |
| Deployment | Docker + a reverse-proxy gateway merging all 4 engines into one hosted service, plus a static frontend build. See [`DEPLOY.md`](DEPLOY.md) |

---

## Module Overview

Each stage ended up as its own independent FastAPI microservice, not four
modules under one `main.py` — every engine defines its own top-level `app`
package (to avoid namespace collisions if two ever ran in the same process),
resolves the previous stage's output from that engine's local storage or live
API by `dataset_id`/`source_job_id`, and writes only to its own `storage/`.
All four are wired together and integration-tested against each other, plus a
separately-owned frontend that calls all four directly from the browser.

| Stage | Folder | Entry point | Port |
|-------|--------|-------------|------|
| 1 — Ingestion & Deep Analysis | `person1_engine/` | `app/main.py` (`/upload`, `/analyze`) | 8000 |
| 2 — Preprocessing Suggestions | `person2_engine/` | `app/suggestion_api.py` (`/suggest`) | 8001 |
| 3 — Execution / Transform (Apply) | `person3_engine/` | `app/apply_api.py` (`/apply`, `/export`) | 8002 |
| 4 — Algorithm Recommendation | `person4_engine/` | `app/recommend_api.py` (`/recommend`) | 8003 |
| Frontend | `frontend/` | React + Vite SPA | 5173 |

Every engine also exposes `GET /health`, `GET /status/{job_id}`, and
`GET /result/{job_id}` following the same shared job-queue pattern
(`get_job_queue()`), so all four poll identically from the frontend's
perspective. See each folder's own README for its exact contract, and
`frontend/README.md` for how the UI ties them together (including two
cross-engine bugs found and fixed during integration).

---

## How to Run

Each engine needs its own virtual environment and its own terminal (they're
independent processes, deliberately — see "Module Overview" above):

```bash
# terminal 1
cd person1_engine && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2
cd person2_engine && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.suggestion_api:app --reload --port 8001

# terminal 3
cd person3_engine && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.apply_api:app --reload --port 8002

# terminal 4
cd person4_engine && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.recommend_api:app --reload --port 8003

# terminal 5
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Then either drive the pipeline through the UI (`/workspace` → Upload →
Analyze → Suggest → Apply & Export → Recommend), or call the four APIs
directly in that order via curl/Postman — each engine's README has a full
curl walkthrough, both standalone (its own fixtures, no other engine needed)
and integrated (chained `dataset_id`/`source_job_id` values).

**Windows + Python 3.14 note:** several engines pin older exact dependency
versions (e.g. `numpy==1.26.4`) that predate Python 3.14 and have no
prebuilt Windows wheel, so `pip install -r requirements.txt` may try to
compile from source and fail. Installing the same package set without exact
version pins (letting pip resolve the latest compatible wheels) works around
this without needing to edit any `requirements.txt`.

---

## Team Framework

| Member | Role | Key Contribution |
|--------|------|------------------|
| **Person 1** | Profiling Lead | Ingestion, deep statistical analysis, outlier detection, `/upload` + `/analyze` endpoints, shared job-queue setup |
| **Person 2** | Suggestion Engine Lead | AutoGluon/auto-sklearn preprocessing pipeline, feature engineering suggestions, redundancy detection, `/suggest` endpoint |
| **Person 3** | Transform Engine Lead | Applying selected suggestions, constraint-based feature selection, conflict resolution, export, `/apply` + `/export` endpoints |
| **Person 4** | Recommendation Engine Lead | Meta-learning algorithm shortlist, live benchmarking, `/recommend` endpoint, end-to-end pipeline integration testing |

---

## Datasets & References

**Test Datasets**
- UCI Machine Learning Repository — https://archive.ics.uci.edu/
- Kaggle Datasets — https://www.kaggle.com/datasets
- OpenML — https://www.openml.org/
- Google Dataset Search — https://datasetsearch.research.google.com/

**Reference Papers**
- AutoML: A Survey of the State-of-the-Art (He et al.) — https://arxiv.org/pdf/1908.00709
- Data Preprocessing Using AutoML: A Survey — https://www.researchgate.net/publication/379721063_Data_Preprocessing_Using_AutoML_A_Survey
- A Survey of Evaluating AutoML and Automated Feature Engineering Tools in Modern Data Science — https://www.scitepress.org/Papers/2025/132667/132667.pdf
- A Survey on Recent Advancements in Auto-Machine Learning with a Focus on Feature Engineering — https://ojs.bonviewpress.com/index.php/JCCE/article/view/720
- Automated data processing and feature engineering for deep learning and big data applications: A survey — https://www.sciencedirect.com/science/article/pii/S2949715924000027
- Curated AutoML paper list (GitHub) — https://github.com/hibayesian/awesome-automl-papers

---

## Future Scope

- Image dataset support (currently sidelined to keep scope tabular-first)
- Persistent storage (a real database instead of local disk) and a process supervisor for the backend container, now that it's actually deployed (see `DEPLOY.md`'s Known Limitations)
- Interactive "focus on this feature" conversational interface
- Automated model training and deployment beyond just recommendation
- Support for time-series and text datasets
- Versioned preprocessing pipelines so users can compare multiple preprocessing runs
