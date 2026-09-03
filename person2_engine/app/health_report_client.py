"""
health_report_client.py — resolves the two inputs the suggestion engine needs:

  1. The Dataset Health Report (dict) — REQUIRED. Core rule-based suggestions
     (imputation/encoding/scaling/transform/drop_redundant/binning/interaction)
     are derived entirely from this report's statistics, so this engine never
     needs Person 1's raw dataset just to produce suggestions.

  2. The raw dataset (pandas DataFrame) — OPTIONAL. Only used to enrich
     suggestions via AutoGluon's feature generator (app/suggestions/automl_enrichment.py).
     When unavailable, enrichment degrades gracefully; nothing else breaks.

Resolution order for the health report:
  a) `health_report` passed inline in the request body — used as-is.
  b) Person 1's shared reports directory on disk (config.PERSON1_REPORTS_DIR /
     f"{source_job_id}.json") — convenience path for local, co-located dev.
  c) A live HTTP call to Person 1's running API (config.PERSON1_API_BASE_URL),
     GET /result/{source_job_id} — convenience path when the two engines run as
     separate services but share a network.

The raw dataset is only ever looked up from Person 1's shared storage
(config.PERSON1_DATASETS_DIR / f"{dataset_id}.parquet") — if that engine isn't
co-located, AutoGluon enrichment is simply skipped with a clear note.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from app import suggestion_config as config


class HealthReportUnavailable(Exception):
    """Raised when no health report could be resolved from any source."""


def resolve_health_report(
    dataset_id: str,
    source_job_id: Optional[str] = None,
    inline_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if inline_report is not None:
        return inline_report

    if source_job_id:
        local_path = config.PERSON1_REPORTS_DIR / f"{source_job_id}.json"
        if local_path.exists():
            import json

            return json.loads(local_path.read_text())

        if config.PERSON1_API_BASE_URL:
            import httpx

            url = f"{config.PERSON1_API_BASE_URL.rstrip('/')}/result/{source_job_id}"
            try:
                resp = httpx.get(url, timeout=30.0)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise HealthReportUnavailable(
                    f"Could not fetch health report from Person 1's API at {url}: {exc}"
                ) from exc

    raise HealthReportUnavailable(
        "No health report available. Pass `health_report` inline in the request body, "
        f"or supply `source_job_id` with either a report at "
        f"{config.PERSON1_REPORTS_DIR}/<source_job_id>.json (co-located Person 1 engine) "
        "or PERSON1_API_BASE_URL set so it can be fetched live from Person 1's /result endpoint."
    )


def try_load_raw_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    """Best-effort only — returns None (never raises) if unavailable, since the
    raw dataset is purely an enrichment input, not a required one."""
    path = config.PERSON1_DATASETS_DIR / f"{dataset_id}.parquet"
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:  # noqa: BLE001 — enrichment input only, never fatal
        return None
