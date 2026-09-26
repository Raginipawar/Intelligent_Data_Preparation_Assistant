"""
recommend_api.py — FastAPI routes for Person 4 Algorithm Recommendation Engine.
"""
from __future__ import annotations

import json
from fastapi import FastAPI, HTTPException, Path as APIPath
from fastapi.middleware.cors import CORSMiddleware
from app import recommend_config as config
from app.jobs.recommend_job_queue import get_job_queue
from app.recommend_pipeline import run_recommend_job
from app.recommend_schemas import RecommendRequest, JobStatus

app = FastAPI(
    title="Person 4 — Algorithm Recommendation Engine",
    version=config.ENGINE_VERSION,
    description="Meta-learning and empirical benchmarking for ML algorithm recommendation.",
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
    return {
        "status": "ok",
        "engine": "person4_engine",
        "version": config.ENGINE_VERSION,
    }


@app.post("/recommend", status_code=202)
def create_recommendation(req: RecommendRequest):
    queue = get_job_queue()
    job_id = queue.new_job(dataset_id=req.dataset_id)

    queue.submit(
        job_id,
        run_recommend_job,
        req.dataset_id,
        job_id,
        req.apply_job_id,
        req.target_column,
        req.perform_benchmark,
        req.top_k_benchmark,
        req.custom_meta_features,
    )

    return {
        "job_id": job_id,
        "dataset_id": req.dataset_id,
        "apply_job_id": req.apply_job_id,
        "status": JobStatus.PENDING.value,
        "status_url": f"/status/{job_id}",
        "result_url": f"/result/{job_id}",
    }


@app.get("/status/{job_id}")
def get_status(job_id: str = APIPath(...)):
    queue = get_job_queue()
    job = queue.get_job(job_id)

    if job is not None:
        return {
            "job_id": job.job_id,
            "dataset_id": job.dataset_id,
            "status": job.status.value,
            "error": job.error,
        }

    # Check disk persistence
    job_disk = config.JOBS_DIR / f"{job_id}.json"
    if job_disk.exists():
        try:
            return json.loads(job_disk.read_text())
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")


@app.get("/result/{job_id}")
def get_result(job_id: str = APIPath(...)):
    queue = get_job_queue()
    job = queue.get_job(job_id)

    if job is not None:
        if job.status == JobStatus.FAILED:
            raise HTTPException(status_code=500, detail=f"Job failed: {job.error}")
        if job.status != JobStatus.SUCCESS:
            raise HTTPException(status_code=409, detail=f"Job is still {job.status.value}.")
        return job.result

    # Check recommendation disk storage
    report_file = config.RECOMMENDATIONS_DIR / f"{job_id}.json"
    if report_file.exists():
        try:
            return json.loads(report_file.read_text())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")

    raise HTTPException(status_code=404, detail=f"Result for job {job_id!r} not found.")
