"""
Live API flow test: POST /apply -> poll GET /status/{job_id} -> GET /result/{job_id}
-> POST /export, using FastAPI's TestClient (no real server/socket needed) with an
inline dataset (via /upload) and inline suggestions, so this test has zero
dependency on Person 1's or Person 2's engines being present or running.
"""
import io
import time
import zipfile

from fastapi.testclient import TestClient

from app.apply_api import app
from sample_data.fake_dataset import build_fake_dataset
from sample_data.fake_suggestion_list import build_fake_suggestions

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


def _upload_fake_dataset() -> str:
    csv_bytes = build_fake_dataset().to_csv(index=False).encode("utf-8")
    resp = client.post("/upload", files={"file": ("fake.csv", csv_bytes, "text/csv")})
    assert resp.status_code == 200
    return resp.json()["dataset_id"]


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_csv():
    dataset_id = _upload_fake_dataset()
    assert dataset_id


def test_upload_zip():
    csv_bytes = build_fake_dataset().to_csv(index=False).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("fake.csv", csv_bytes)
    resp = client.post("/upload", files={"file": ("fake.zip", buf.getvalue(), "application/zip")})
    assert resp.status_code == 200
    assert resp.json()["dataset_id"]


def test_apply_requires_suggestions_or_source_job_id():
    resp = client.post("/apply", json={"dataset_id": "ds1", "selected_suggestion_ids": ["x"]})
    assert resp.status_code == 400


def test_apply_requires_nonempty_selection():
    resp = client.post(
        "/apply", json={"dataset_id": "ds1", "selected_suggestion_ids": [], "suggestions": []}
    )
    assert resp.status_code == 400


def test_full_apply_and_export_flow():
    dataset_id = _upload_fake_dataset()
    suggestions = build_fake_suggestions()
    selected = ["imputation_age", "imputation_monthly_charges", "encoding_contract", "scaling_age"]

    resp = client.post(
        "/apply",
        json={
            "dataset_id": dataset_id,
            "selected_suggestion_ids": selected,
            "suggestions": suggestions,
            "feature_budget": None,
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "pending"

    final_status = _wait_for_job(job_id)
    assert final_status == "success"

    result = client.get(f"/result/{job_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["dataset_id"] == dataset_id
    assert set(body["applied_suggestions"]) == set(selected)
    assert body["n_columns"] > 0
    assert len(body["transformation_log"]) >= len(selected)

    export_resp = client.post("/export", json={"apply_job_id": job_id, "format": "csv"})
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/csv")
    assert b"tenure_months" in export_resp.content

    export_zip_resp = client.post("/export", json={"apply_job_id": job_id, "format": "zip"})
    assert export_zip_resp.status_code == 200
    assert export_zip_resp.headers["content-type"] == "application/zip"


def test_result_for_unknown_job_returns_404():
    resp = client.get("/result/does-not-exist")
    assert resp.status_code == 404


def test_export_for_unknown_job_returns_404():
    resp = client.post("/export", json={"apply_job_id": "does-not-exist", "format": "csv"})
    assert resp.status_code == 404


def test_apply_with_unresolvable_dataset_id_fails_job_not_endpoint():
    resp = client.post(
        "/apply",
        json={
            "dataset_id": "no-such-dataset",
            "selected_suggestion_ids": ["imputation_age"],
            "suggestions": build_fake_suggestions(),
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    final_status = _wait_for_job(job_id)
    assert final_status == "failed"

    result = client.get(f"/result/{job_id}")
    assert result.status_code == 500
