import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DATASETS_DIR = STORAGE_DIR / "datasets"
JOBS_DIR = STORAGE_DIR / "jobs"
APPLIED_DIR = STORAGE_DIR / "applied"
EXPORTS_DIR = STORAGE_DIR / "exports"

for d in (STORAGE_DIR, DATASETS_DIR, JOBS_DIR, APPLIED_DIR, EXPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# "memory"  -> in-process ThreadPoolExecutor, zero external dependencies (default).
# "celery"  -> Celery + Redis, same opt-in pattern Person 1 defined in person1_engine/app/jobs/queue.py.
JOB_QUEUE_BACKEND = os.environ.get("JOB_QUEUE_BACKEND", "memory")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
# Different Redis result-backend DB index than Person 1 (/1) and Person 2 (/2),
# so all three engines can share one Redis instance without clobbering results.
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")

THREAD_POOL_WORKERS = int(os.environ.get("THREAD_POOL_WORKERS", "4"))

# --- Cross-engine lookup (convenience only) ---
# Person 3 never imports Person 1's or Person 2's Python packages directly (all three
# engines define their own top-level `app` package; importing across them would collide
# the moment two ran in the same process). Instead this engine reads the other two
# engines' *storage files* directly when a caller only supplies IDs, or calls their
# *live APIs*. Both raw dataset and suggestion list can also be supplied inline, which
# keeps this engine fully decoupled and independently testable/demoable.
PERSON1_STORAGE_DIR = Path(
    os.environ.get("PERSON1_STORAGE_DIR", str(BASE_DIR.parent / "person1_engine" / "storage"))
)
PERSON1_DATASETS_DIR = PERSON1_STORAGE_DIR / "datasets"

# Person 2's engine lives in its own person2_engine/ folder, a sibling of this
# engine's own BASE_DIR — same layout as Person 1's engine above.
PERSON2_STORAGE_DIR = Path(
    os.environ.get("PERSON2_STORAGE_DIR", str(BASE_DIR.parent / "person2_engine" / "storage"))
)
PERSON2_SUGGESTIONS_DIR = PERSON2_STORAGE_DIR / "suggestions"

# If set (e.g. "http://localhost:8000" / "http://localhost:8001"), missing local files
# fall back to a live HTTP call against the other engine's /result endpoint.
PERSON1_API_BASE_URL = os.environ.get("PERSON1_API_BASE_URL", "")
PERSON2_API_BASE_URL = os.environ.get("PERSON2_API_BASE_URL", "")

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))

# Default cap on final feature count when a request doesn't specify feature_budget.
# None means "no budget enforced" — feature_selection.py only trims when a budget
# (request-level or this default) is actually set.
DEFAULT_FEATURE_BUDGET = os.environ.get("DEFAULT_FEATURE_BUDGET")
DEFAULT_FEATURE_BUDGET = int(DEFAULT_FEATURE_BUDGET) if DEFAULT_FEATURE_BUDGET else None

ENGINE_VERSION = "1.0.0"
