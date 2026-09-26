"""
export.py — writes the final processed dataset back out as a file, matching
the user's original upload format by default ("auto": single CSV -> .csv,
any ZIP-sourced dataset -> .zip containing the CSV), or an explicit override.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd

from app import apply_config as config


class ExportUnavailable(Exception):
    """Raised when the requested apply_job_id has no processed dataset to export."""


def _applied_dataset_path(apply_job_id: str) -> Path:
    return config.APPLIED_DIR / f"{apply_job_id}.parquet"


def _applied_meta_path(apply_job_id: str) -> Path:
    return config.APPLIED_DIR / f"{apply_job_id}.meta.json"


def read_source_type(apply_job_id: str) -> Optional[str]:
    meta_path = _applied_meta_path(apply_job_id)
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text()).get("source_type")


def _resolve_format(fmt: str, source_type: Optional[str]) -> str:
    if fmt in ("csv", "zip"):
        return fmt
    if fmt == "auto":
        return "zip" if (source_type or "").startswith("zip") else "csv"
    raise ValueError(f"Unknown export format {fmt!r} — expected 'csv', 'zip', or 'auto'")


def export_dataset(apply_job_id: str, fmt: str = "auto") -> tuple[bytes, str, str]:
    """Returns (file_bytes, filename, media_type)."""
    dataset_path = _applied_dataset_path(apply_job_id)
    if not dataset_path.exists():
        raise ExportUnavailable(
            f"No processed dataset found for apply_job_id={apply_job_id!r}. "
            "Call POST /apply and wait for it to succeed first."
        )

    df = pd.read_parquet(dataset_path)
    resolved = _resolve_format(fmt, read_source_type(apply_job_id))

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    if resolved == "csv":
        filename = f"{apply_job_id}.csv"
        (config.EXPORTS_DIR / filename).write_bytes(csv_bytes)
        return csv_bytes, filename, "text/csv"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("processed_dataset.csv", csv_bytes)
    zip_bytes = buf.getvalue()
    filename = f"{apply_job_id}.zip"
    (config.EXPORTS_DIR / filename).write_bytes(zip_bytes)
    return zip_bytes, filename, "application/zip"
