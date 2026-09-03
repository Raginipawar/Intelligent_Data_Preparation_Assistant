import io
import time
import zipfile

import pandas as pd
from fastapi.testclient import TestClient

from app.ingestion.loader import load_upload
from app.main import app
from app.schemas import SourceType

client = TestClient(app)


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_single_csv_in_zip():
    csv_bytes = b"a,b\n1,2\n3,4\n"
    zip_bytes = _make_zip({"data.csv": csv_bytes.decode()})
    result = load_upload(zip_bytes, "data.zip")
    assert result.source_type == SourceType.ZIP_SINGLE_CSV
    assert len(result.df) == 2


def test_csv_with_supporting_files_in_zip():
    csv_bytes = "a,b\n1,2\n3,4\n"
    zip_bytes = _make_zip({"data.csv": csv_bytes, "readme.txt": "some notes", "schema.json": "{}"})
    result = load_upload(zip_bytes, "data.zip")
    assert result.source_type == SourceType.ZIP_MULTI_CSV_WITH_SUPPORTING
    assert len(result.supporting_files) == 2


def test_multi_csv_joined_on_shared_key():
    customers = "customer_id,name\n1,Alice\n2,Bob\n"
    orders = "customer_id,amount\n1,50\n2,75\n"
    zip_bytes = _make_zip({"customers.csv": customers, "orders.csv": orders})
    result = load_upload(zip_bytes, "data.zip")
    assert result.source_type == SourceType.ZIP_MULTI_CSV_JOINED
    assert "name" in result.df.columns and "amount" in result.df.columns


def test_multi_csv_no_shared_key_falls_back_to_largest():
    a = "col1,col2\n1,2\n3,4\n5,6\n"
    b = "colX,colY\n9,9\n"
    zip_bytes = _make_zip({"big.csv": a, "small.csv": b})
    result = load_upload(zip_bytes, "data.zip")
    assert result.source_type == SourceType.ZIP_MULTI_CSV_WITH_SUPPORTING
    assert result.primary_file == "big.csv"
    assert len(result.df) == 3


def test_semicolon_delimiter_detected():
    csv_bytes = b"a;b;c\n1;2;3\n4;5;6\n"
    result = load_upload(csv_bytes, "euro.csv")
    assert result.delimiter == ";"
    assert list(result.df.columns) == ["a", "b", "c"]


# --- Full API flow ---


def test_full_api_flow_upload_analyze_poll_result():
    df = pd.DataFrame(
        {
            "age": list(range(20, 70)) * 2,
            "salary": [30000 + i * 500 for i in range(100)],
            "department": (["Eng", "Sales", "HR"] * 34)[:100],
            "target": ([0, 1] * 50),
        }
    )
    csv_bytes = df.to_csv(index=False).encode()

    upload_resp = client.post("/upload", files={"file": ("employees.csv", csv_bytes, "text/csv")})
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]
    assert upload_resp.json()["ingestion"]["n_rows"] == 100

    analyze_resp = client.post(f"/analyze?dataset_id={dataset_id}")
    assert analyze_resp.status_code == 200
    job_id = analyze_resp.json()["job_id"]

    for _ in range(50):
        status_resp = client.get(f"/status/{job_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()["status"]
        if status == "success":
            break
        if status == "failed":
            raise AssertionError(f"Job failed: {status_resp.json()['error']}")
        time.sleep(0.1)
    else:
        raise AssertionError("Job did not finish in time")

    result_resp = client.get(f"/result/{job_id}")
    assert result_resp.status_code == 200
    report = result_resp.json()
    assert report["dataset_id"] == dataset_id
    assert report["target_detection"]["suggested_target"] == "target"
    assert report["feature_importance_signal"]["ran"] is True


def test_unknown_job_id_returns_404():
    resp = client.get("/status/does-not-exist")
    assert resp.status_code == 404


def test_unknown_dataset_id_returns_404():
    resp = client.post("/analyze?dataset_id=does-not-exist")
    assert resp.status_code == 404


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
