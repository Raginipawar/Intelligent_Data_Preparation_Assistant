# Person 4 — Algorithm Recommendation Engine

Takes the final processed dataset from Person 3 (or direct dataset upload/meta-features), extracts meta-features, performs meta-learning candidate algorithm matching, generates data-backed reasoning explanations, runs an optional fast empirical cross-validation benchmark, and returns a structured **Algorithm Recommendation Report**.

---

## What's Implemented

### 1. Meta-Feature Extractor (`app/meta_features.py`)
- **Dimensionality & Shape:** `n_rows`, `n_columns`, `n_features`, `feature_to_sample_ratio` ($D/N$).
- **Task Type Detection:** Auto-detects `binary_classification`, `multiclass_classification`, or `regression` from the target column cardinality and dtype.
- **Feature Composition:** Counts `n_numerical`, `n_categorical`, `n_boolean`, `n_text`, and `n_datetime` features.
- **Statistical Profiling:** `class_imbalance_ratio`, `missing_cell_pct`, `high_skew_count`, and `mean_absolute_correlation` (multicollinearity metric).

### 2. Meta-Learning Candidate Scoring Engine (`app/recommend_engine.py`)
- **Supported Candidate Algorithms:**
  - **Classification:** `RandomForestClassifier`, `GradientBoostingClassifier`, `HistGradientBoostingClassifier`, `ExtraTreesClassifier`, `LogisticRegression`, `SVC`, `KNeighborsClassifier`.
  - **Regression:** `RandomForestRegressor`, `GradientBoostingRegressor`, `HistGradientBoostingRegressor`, `ExtraTreesRegressor`, `Ridge`, `SVR`, `KNeighborsRegressor`.
- **Meta-Learning Weights:** Scores algorithms dynamically based on observed meta-features (e.g., sample size thresholds, feature-to-sample ratio, class imbalance, mixed feature dtypes, multicollinearity).

### 3. Data-Backed Reasoning Generator (`app/reasoning_generator.py`)
- Produces explicit, readable reasoning arrays tied directly to measurable dataset characteristics rather than hardcoded generic text.

### 4. Fast Empirical Cross-Validation Benchmarker (`app/benchmarker.py`)
- Runs 5-fold cross-validation on top $K$ candidates (default top 3).
- Uses leak-free `ColumnTransformer` (median impute + StandardScaler for numeric, most-frequent impute + OneHotEncoder for categorical).
- Selects metric based on task type (Accuracy / F1-macro for classification, R² for regression).

### 5. FastAPI & Shared Job Queue (`app/recommend_api.py`, `app/jobs/recommend_job_queue.py`)
- `POST /recommend` — Async job submission returning `job_id` and `status: pending`.
- `GET /status/{job_id}` — Poll job execution state.
- `GET /result/{job_id}` — Retrieve the completed `Algorithm Recommendation Report`.
- `GET /health` — Service health check.
- Uses the identical `get_job_queue()` pattern as Persons 1–3.

---

## Quick Start

```bash
cd person4_engine
pip install -r requirements.txt
python -m uvicorn app.recommend_api:app --reload --port 8003
```

### Running Tests

```bash
set PYTHONPATH=.    # On Windows PowerShell: $env:PYTHONPATH="."
pytest tests/ -v
```

---

## API Request / Response Example

### Request: `POST http://localhost:8003/recommend`

```json
{
  "dataset_id": "churn_demo",
  "apply_job_id": "apply-job-12345",
  "target_column": "churn",
  "perform_benchmark": true,
  "top_k_benchmark": 3
}
```

### Response: `GET http://localhost:8003/result/{job_id}`

```json
{
  "status": "success",
  "job_id": "f47b2c1e-9a8b-4c3d-8e7f-6a5b4c3d2e1f",
  "dataset_id": "churn_demo",
  "apply_job_id": "apply-job-12345",
  "task_type": "binary_classification",
  "target_column": "churn",
  "dataset_meta_features": {
    "n_rows": 500,
    "n_columns": 7,
    "n_features": 6,
    "feature_to_sample_ratio": 0.012,
    "task_type": "binary_classification",
    "target_column": "churn",
    "target_cardinality": 2,
    "n_numerical": 4,
    "n_categorical": 1,
    "n_boolean": 1,
    "n_text": 0,
    "n_datetime": 0,
    "class_imbalance_ratio": 3.0,
    "missing_cell_pct": 0.0,
    "high_skew_count": 1,
    "mean_absolute_correlation": 0.12
  },
  "recommendations": [
    {
      "algorithm": "GradientBoostingClassifier",
      "model_class": "sklearn.ensemble.GradientBoostingClassifier",
      "rank": 1,
      "recommendation_score": 0.94,
      "reasoning": [
        "Dataset contains 500 rows, providing a balanced volume suitable for standard cross-validated estimators.",
        "Contains 1 categorical and 1 boolean features; tree-based models split natively across mixed feature types.",
        "Noticed significant class imbalance (ratio 3.0:1); tree ensembles allow class weighting and handle thresholding effectively."
      ],
      "benchmark": {
        "metric": "accuracy",
        "score": 0.784,
        "cv_scores": [0.79, 0.77, 0.78, 0.79, 0.79],
        "fit_time_seconds": 0.32,
        "status": "completed"
      },
      "suitability": "high"
    }
  ],
  "benchmarked": true,
  "meta": {
    "engine_version": "1.0.0",
    "processing_time_seconds": 1.25
  }
}
```
