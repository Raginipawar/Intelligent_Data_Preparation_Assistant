import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
SUGGESTIONS_DIR = STORAGE_DIR / "suggestions"
JOBS_DIR = STORAGE_DIR / "jobs"

for d in (STORAGE_DIR, SUGGESTIONS_DIR, JOBS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# "memory"  -> in-process ThreadPoolExecutor, zero external dependencies (default).
# "celery"  -> Celery + Redis, same opt-in pattern Person 1 defined in person1_engine/app/jobs/queue.py.
JOB_QUEUE_BACKEND = os.environ.get("JOB_QUEUE_BACKEND", "memory")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
# Different Redis result-backend DB index than Person 1's (../person1_engine uses /1),
# so both engines can point at the same Redis instance without clobbering results.
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

THREAD_POOL_WORKERS = int(os.environ.get("THREAD_POOL_WORKERS", "4"))

# --- Cross-engine lookup (convenience only — see app/health_report_client.py) ---
# Person 2 never imports Person 1's Python package directly (both engines define their
# own top-level `app` package; importing across them would collide). Instead, when a
# caller supplies only a dataset_id/source_job_id (no inline health_report), this engine
# optionally reads Person 1's *storage files* directly, or calls Person 1's *live API*.
# Neither path is required: POST /suggest also accepts the full health_report JSON inline,
# which keeps this engine fully decoupled and independently testable/demoable.
PERSON1_STORAGE_DIR = Path(
    os.environ.get("PERSON1_STORAGE_DIR", str(BASE_DIR.parent / "person1_engine" / "storage"))
)
PERSON1_DATASETS_DIR = PERSON1_STORAGE_DIR / "datasets"
PERSON1_REPORTS_DIR = PERSON1_STORAGE_DIR / "reports"

# If set (e.g. "http://localhost:8000"), /suggest will fetch a missing health report via
# GET {PERSON1_API_BASE_URL}/result/{source_job_id} instead of reading PERSON1_REPORTS_DIR.
PERSON1_API_BASE_URL = os.environ.get("PERSON1_API_BASE_URL", "")

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))

# --- Suggestion-engine thresholds (all overridable via env for experimentation) ---
SKEW_TRANSFORM_THRESHOLD = float(os.environ.get("SKEW_TRANSFORM_THRESHOLD", "1.0"))
LOW_CARDINALITY_ONEHOT_MAX = int(os.environ.get("LOW_CARDINALITY_ONEHOT_MAX", "15"))
REDUNDANCY_CORR_THRESHOLD = float(os.environ.get("REDUNDANCY_CORR_THRESHOLD", "0.9"))
HIGH_MISSING_REVIEW_PCT = float(os.environ.get("HIGH_MISSING_REVIEW_PCT", "50.0"))
LOW_MISSING_MODE_PCT = float(os.environ.get("LOW_MISSING_MODE_PCT", "5.0"))
BINNING_MIN_UNIQUE = int(os.environ.get("BINNING_MIN_UNIQUE", "10"))
BINNING_MAX_UNIQUE = int(os.environ.get("BINNING_MAX_UNIQUE", "50"))
BINNING_SKEW_THRESHOLD = float(os.environ.get("BINNING_SKEW_THRESHOLD", "1.5"))
INTERACTION_TOP_K = int(os.environ.get("INTERACTION_TOP_K", "3"))
INTERACTION_REDUNDANCY_CORR = float(os.environ.get("INTERACTION_REDUNDANCY_CORR", "0.7"))

# AutoGluon feature-generator enrichment (optional, lazily imported — see
# app/suggestions/automl_enrichment.py). Never a hard dependency of the core rule engine.
AUTOGLUON_ENRICHMENT_ENABLED = os.environ.get("AUTOGLUON_ENRICHMENT_ENABLED", "true").lower() == "true"

ENGINE_VERSION = "1.0.0"
