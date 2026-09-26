"""
recommend_config.py — configuration settings for person4_engine.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"
RECOMMENDATIONS_DIR = STORAGE_DIR / "recommendations"
JOBS_DIR = STORAGE_DIR / "jobs"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Shared job queue backend config
JOB_QUEUE_BACKEND = os.getenv("JOB_QUEUE_BACKEND", "in_memory")
THREAD_POOL_WORKERS = int(os.getenv("THREAD_POOL_WORKERS", "4"))
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Base URLs for inter-engine communication
PERSON1_API_BASE_URL = os.getenv("PERSON1_API_BASE_URL", "http://localhost:8000")
PERSON2_API_BASE_URL = os.getenv("PERSON2_API_BASE_URL", "http://localhost:8001")
PERSON3_API_BASE_URL = os.getenv("PERSON3_API_BASE_URL", "http://localhost:8002")

# Relative storage locations for co-located deployments
PERSON1_STORAGE_DIR = (BASE_DIR.parent / "person1_engine" / "storage").resolve()
PERSON3_STORAGE_DIR = (BASE_DIR.parent / "person3_engine" / "storage").resolve()

# Engine metadata
ENGINE_VERSION = "1.0.0"
DEFAULT_BENCHMARK_TOP_K = 3
BENCHMARK_TIMEOUT_SECONDS = 30
