"""
suggestion_client.py — resolves the other required input: Person 2's ranked
Suggestion List. Same 3-tier resolution order as Person 2's own
health_report_client.resolve_health_report:

  a) `suggestions` passed inline in the request body — used as-is.
  b) Person 2's shared suggestions directory on disk (config.PERSON2_SUGGESTIONS_DIR /
     f"{source_job_id}.json") — convenience path for local, co-located dev.
  c) A live HTTP call to Person 2's running API (config.PERSON2_API_BASE_URL),
     GET /result/{source_job_id} — convenience path when engines run as
     separate services but share a network.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app import apply_config as config


class SuggestionListUnavailable(Exception):
    """Raised when no suggestion list could be resolved from any source."""


def resolve_suggestions(
    source_job_id: Optional[str] = None,
    inline_suggestions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    if inline_suggestions is not None:
        return inline_suggestions

    if source_job_id:
        local_path = config.PERSON2_SUGGESTIONS_DIR / f"{source_job_id}.json"
        if local_path.exists():
            payload = json.loads(local_path.read_text())
            return payload.get("suggestions", [])

        if config.PERSON2_API_BASE_URL:
            import httpx

            url = f"{config.PERSON2_API_BASE_URL.rstrip('/')}/result/{source_job_id}"
            try:
                resp = httpx.get(url, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("suggestions", [])
            except httpx.HTTPError as exc:
                raise SuggestionListUnavailable(
                    f"Could not fetch suggestion list from Person 2's API at {url}: {exc}"
                ) from exc

    raise SuggestionListUnavailable(
        "No suggestion list available. Pass `suggestions` inline in the request body, "
        f"or supply `source_job_id` with either a suggestion list at "
        f"{config.PERSON2_SUGGESTIONS_DIR}/<source_job_id>.json (co-located Person 2 engine) "
        "or PERSON2_API_BASE_URL set so it can be fetched live from Person 2's /result endpoint."
    )
