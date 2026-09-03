import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DATASETS_DIR = STORAGE_DIR / "datasets"
JOBS_DIR = STORAGE_DIR / "jobs"
REPORTS_DIR = STORAGE_DIR / "reports"

for d in (STORAGE_DIR, DATASETS_DIR, JOBS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# "memory"  -> in-process ThreadPoolExecutor, zero external dependencies (default, works out of the box)
# "celery"  -> Celery + Redis, for when the team wants real distributed workers.
#              Requires a running Redis instance and `celery`/`redis` installed.
JOB_QUEUE_BACKEND = os.environ.get("JOB_QUEUE_BACKEND", "memory")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))
THREAD_POOL_WORKERS = int(os.environ.get("THREAD_POOL_WORKERS", "4"))

# Isolation Forest / distance baseline defaults
ISOLATION_FOREST_CONTAMINATION = float(os.environ.get("IF_CONTAMINATION", "0.05"))
DISTANCE_BASELINE_PERCENTILE = float(os.environ.get("DIST_PERCENTILE", "97.5"))

# Cardinality
HIGH_CARDINALITY_RATIO_THRESHOLD = 0.9

ENGINE_VERSION = "1.0.0"
