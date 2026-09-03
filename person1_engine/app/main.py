"""
main.py — Person 1's FastAPI surface: ingestion + deep analysis.

Endpoints:
  POST /upload            -> fast synchronous parse; returns dataset_id + basic schema
  POST /analyze           -> kicks off the heavy statistical/ML pass as a background job
  GET  /status/{job_id}   -> poll job status
  GET  /result/{job_id}   -> fetch the finished Dataset Health Report
  GET  /health            -> liveness check

This is the pipeline's entry point, so this file also defines the shared
job-queue usage pattern (see app/jobs/queue.py) that Persons 2-4 plug their
own /suggest, /apply, /export, /recommend steps into — same
new_job() -> submit() -> get_job() flow, same dataset_id handoff.
"""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app import config, pipeline
from app.jobs.queue import get_job_queue
from app.schemas import JobStatus

app = FastAPI(
    title="Person 1 — Ingestion & Deep Analysis Engine",
    description="Turns a raw CSV/ZIP upload into a structured Dataset Health Report.",
    version=config.ENGINE_VERSION,
)


@app.get("/health")
def health():
    return {"status": "ok", "engine_version": config.ENGINE_VERSION}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Fast, synchronous. Parses the file and stores it — returns a
    dataset_id that /analyze (and eventually Person 2's /suggest, etc.)
    will reference. Does NOT run the heavy statistical analysis."""
    raw_bytes = await file.read()
    size_mb = len(raw_bytes) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise HTTPException(413, f"File too large ({size_mb:.1f} MB > {config.MAX_UPLOAD_MB} MB limit)")

    if not file.filename:
        raise HTTPException(400, "Uploaded file has no filename")

    try:
        result = pipeline.ingest_upload(raw_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Failed to ingest file: {exc}") from exc

    return JSONResponse(result)


@app.post("/analyze")
def analyze(dataset_id: str):
    """Submits the full Dataset Health Report computation to the shared job
    queue. Returns immediately with a job_id to poll — large datasets can
    take a while (Isolation Forest + LightGBM aren't instant)."""
    dataset_path = config.DATASETS_DIR / f"{dataset_id}.parquet"
    if not dataset_path.exists():
        raise HTTPException(404, f"Unknown dataset_id {dataset_id!r} — call /upload first")

    queue = get_job_queue()
    job_id = queue.new_job(dataset_id=dataset_id)
    queue.submit(job_id, pipeline.run_full_analysis, dataset_id, job_id)

    return {"job_id": job_id, "dataset_id": dataset_id, "status": JobStatus.PENDING}


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
        raise HTTPException(500, f"Job failed: {record.error}")
    if record.status != JobStatus.SUCCESS:
        raise HTTPException(202, f"Job not finished yet (status={record.status.value})")
    return JSONResponse(record.result)
