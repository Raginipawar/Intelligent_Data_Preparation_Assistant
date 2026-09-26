"""
test_api.py — Tests FastAPI endpoints for Person 4 using TestClient.
"""
from fastapi.testclient import TestClient
from app.recommend_api import app
from sample_data.generate_sample import generate

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_recommend_endpoint_standalone(tmp_path, monkeypatch):
    # Generate sample dataset first
    from app import recommend_config
    sample_dir = recommend_config.BASE_DIR / "sample_data"
    sample_dir.mkdir(parents=True, exist_ok=True)

    from sample_data.generate_sample import generate
    generate()

    body = {
        "dataset_id": "sample_churn",
        "perform_benchmark": True,
        "top_k_benchmark": 2,
    }
    resp = client.post("/recommend", json=body)
    assert resp.status_code == 202
    job_data = resp.json()
    job_id = job_data["job_id"]
    assert job_data["status"] == "pending"

    # Poll status until success
    import time
    for _ in range(30):
        status_resp = client.get(f"/status/{job_id}")
        assert status_resp.status_code == 200
        if status_resp.json()["status"] == "success":
            break
        time.sleep(0.3)

    # Fetch result
    result_resp = client.get(f"/result/{job_id}")
    assert result_resp.status_code == 200
    res_data = result_resp.json()
    assert res_data["dataset_id"] == "sample_churn"
    assert len(res_data["recommendations"]) > 0
    assert res_data["benchmarked"] is True
