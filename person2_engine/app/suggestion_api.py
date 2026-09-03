"""
main.py — Person 2's FastAPI surface: preprocessing & feature-engineering
suggestions.

Endpoints:
  POST /suggest            -> kicks off suggestion generation as a background job
  GET  /status/{job_id}    -> poll job status
  GET  /result/{job_id}    -> fetch the finished Suggestion List
  GET  /health             -> liveness check

Mirrors Person 1's /analyze -> /status -> /result polling shape exactly (see
person1_engine/app/main.py) for a consistent client experience across both
engines, and uses the same get_job_queue() pattern (app/jobs/suggestion_job_queue.py).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app import suggestion_config as config
from app.health_report_client import HealthReportUnavailable
from app.jobs.suggestion_job_queue import get_job_queue
from app.suggestion_schemas import JobStatus, SuggestRequest
from app import suggestion_pipeline as pipeline

app = FastAPI(
    title="Person 2 — Preprocessing & Feature Engineering Suggestion Engine",
    description=(
        "Consumes Person 1's Dataset Health Report and returns a ranked, reasoned "
        "list of preprocessing/feature-engineering suggestions for Person 3 to apply."
    ),
    version=config.ENGINE_VERSION,
)


@app.get("/health")
def health():
    return {"status": "ok", "engine_version": config.ENGINE_VERSION}


@app.post("/suggest")
def suggest(request: SuggestRequest):
    """Submits suggestion generation to the shared job queue. Returns immediately
    with a job_id to poll — see README for the full request-body shape (inline
    health_report vs. dataset_id/source_job_id lookup)."""
    if request.health_report is None and not request.source_job_id:
        raise HTTPException(
            400,
            "Provide either `health_report` inline, or `source_job_id` so this engine can "
            "look it up from Person 1's shared storage/API. See README for details.",
        )

    queue = get_job_queue()
    job_id = queue.new_job(dataset_id=request.dataset_id)
    queue.submit(
        job_id,
        pipeline.run_suggestion_job,
        request.dataset_id,
        job_id,
        request.source_job_id,
        request.health_report,
    )

    return {"job_id": job_id, "dataset_id": request.dataset_id, "status": JobStatus.PENDING}


@app.get("/status/{job_id}")
def status(job_id: str):
    queue = get_job_queue()
    record = queue.get_job(job_id)
    if record is None:
        raise HTTPException(404, f"Unknown job_id {job_id!r}")
    return {
        "job_id": record.job_id,
        "dataset_id": record.dataset_id,
        "status": record.status,
        "error": record.error,
    }


@app.get("/result/{job_id}")
def result(job_id: str):
    queue = get_job_queue()
    record = queue.get_job(job_id)
    if record is None:
        raise HTTPException(404, f"Unknown job_id {job_id!r}")
    if record.status == JobStatus.FAILED:
        if record.error and "HealthReportUnavailable" in record.error:
            raise HTTPException(404, f"Job failed: {record.error.splitlines()[0]}")
        raise HTTPException(500, f"Job failed: {record.error}")
    if record.status != JobStatus.SUCCESS:
        raise HTTPException(202, f"Job not finished yet (status={record.status.value})")
    return JSONResponse(record.result)
