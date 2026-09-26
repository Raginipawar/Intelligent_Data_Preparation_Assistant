"""
apply_api.py — Person 3's FastAPI surface: execution/transform (apply) layer.

Endpoints:
  POST /upload            -> minimal standalone ingestion (own storage; convenience
                              only — the primary path is a dataset_id already in
                              Person 1's co-located storage)
  POST /apply              -> applies the selected suggestions as a background job
  GET  /status/{job_id}    -> poll job status
  GET  /result/{job_id}    -> fetch the finished ApplyResult (transformation log etc.)
  POST /export              -> returns the processed dataset as a CSV or ZIP file
  GET  /health

Mirrors Person 1's /upload -> /analyze -> /status -> /result shape and Person
2's /suggest -> /status -> /result shape, using the same get_job_queue()
pattern (app/jobs/apply_job_queue.py).
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import apply_config as config
from app import apply_pipeline as pipeline
from app.apply_schemas import ApplyRequest, ExportRequest, JobStatus
from app.dataset_client import store_own_dataset
from app.export import ExportUnavailable, export_dataset
from app.jobs.apply_job_queue import get_job_queue

app = FastAPI(
    title="Person 3 — Execution / Transform Engine (Apply Layer)",
    description=(
        "Applies a user-selected subset of Person 2's suggestions to the raw dataset, "
        "resolving conflicts and enforcing a feature budget, and produces the final "
        "cleaned dataset + transformation log for Person 4 to consume."
    ),
    version=config.ENGINE_VERSION,
)

# The frontend (frontend/, Vite dev server) calls this API directly from the
# browser, so it needs CORS — wide open here since this is local-first dev,
# not a deployed service. Tighten allow_origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "engine_version": config.ENGINE_VERSION}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Fast, synchronous, standalone-testing convenience — parses a CSV or ZIP
    and stores it in this engine's own storage. Not the primary path: in the
    real pipeline the dataset_id already exists in Person 1's storage."""
    raw_bytes = await file.read()
    size_mb = len(raw_bytes) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise HTTPException(413, f"File too large ({size_mb:.1f} MB > {config.MAX_UPLOAD_MB} MB limit)")
    if not file.filename:
        raise HTTPException(400, "Uploaded file has no filename")

    is_zip = file.filename.lower().endswith(".zip") or zipfile.is_zipfile(io.BytesIO(raw_bytes))
    try:
        if is_zip:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not csv_names:
                    raise ValueError("ZIP contains no CSV files — nothing to ingest.")
                df = pd.read_csv(io.BytesIO(zf.read(csv_names[0])))
            source_type = "zip_single_csv"
        else:
            df = pd.read_csv(io.BytesIO(raw_bytes))
            source_type = "single_csv"
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Failed to parse {file.filename}: {exc}") from exc

    dataset_id = store_own_dataset(df, source_type=source_type, primary_file=file.filename)
    return {"dataset_id": dataset_id, "n_rows": int(len(df)), "n_columns": int(len(df.columns))}


@app.post("/apply")
def apply_endpoint(request: ApplyRequest):
    """Submits suggestion application to the shared job queue. Returns
    immediately with a job_id to poll."""
    if request.suggestions is None and not request.source_job_id:
        raise HTTPException(
            400,
            "Provide either `suggestions` inline, or `source_job_id` so this engine can "
            "look up Person 2's ranked list from shared storage/API. See README for details.",
        )
    if not request.selected_suggestion_ids:
        raise HTTPException(400, "`selected_suggestion_ids` must be a non-empty list.")

    queue = get_job_queue()
    job_id = queue.new_job(dataset_id=request.dataset_id)
    queue.submit(
        job_id,
        pipeline.run_apply_job,
        request.dataset_id,
        job_id,
        request.selected_suggestion_ids,
        request.source_job_id,
        request.suggestions,
        request.feature_budget,
        request.target_column,
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
        raise HTTPException(500, f"Job failed: {record.error}")
    if record.status != JobStatus.SUCCESS:
        raise HTTPException(202, f"Job not finished yet (status={record.status.value})")
    return JSONResponse(record.result)


@app.post("/export")
def export_endpoint(request: ExportRequest):
    try:
        file_bytes, filename, media_type = export_dataset(request.apply_job_id, request.format)
    except ExportUnavailable as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
