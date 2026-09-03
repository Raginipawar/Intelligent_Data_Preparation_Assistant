"""
Live API flow test: POST /suggest -> poll GET /status/{job_id} -> GET /result/{job_id},
using FastAPI's TestClient (no real server/socket needed) with an inline health_report
so this test has zero dependency on Person 1's engine being present or running.

Run: pytest -v tests/test_api.py
"""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _wait_for_job(job_id: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/status/{job_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in ("success", "failed"):
            return status
        time.sleep(0.05)
    raise TimeoutError(f"job {job_id} did not finish within {timeout}s")


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_suggest_requires_health_report_or_source_job_id():
    resp = client.post("/suggest", json={"dataset_id": "ds1"})
    assert resp.status_code == 400


def test_full_suggest_flow_with_inline_health_report():
    from sample_data.fake_health_report import build_fake_health_report

    resp = client.post("/suggest", json={"dataset_id": "ds1", "health_report": build_fake_health_report()})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "pending"

    final_status = _wait_for_job(job_id)
    assert final_status == "success"

    result = client.get(f"/result/{job_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["dataset_id"] == "ds1"
    assert len(body["suggestions"]) > 0
    assert body["suggestions"][0]["priority_rank"] == 1


def test_result_for_unknown_job_returns_404():
    resp = client.get("/result/does-not-exist")
    assert resp.status_code == 404


def test_suggest_with_unresolvable_source_job_id_fails_job_not_endpoint():
    resp = client.post("/suggest", json={"dataset_id": "ds1", "source_job_id": "no-such-job"})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    final_status = _wait_for_job(job_id)
    assert final_status == "failed"

    result = client.get(f"/result/{job_id}")
    assert result.status_code == 404  # surfaced as a clear 404, not a raw 500 traceback
