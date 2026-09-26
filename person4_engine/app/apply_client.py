"""
apply_client.py — Resolves processed DataFrame + metadata from Person 3 storage,
Person 1 storage, or direct local path/inline dataset.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from app import recommend_config as config


def resolve_processed_dataset(
    dataset_id: str,
    apply_job_id: Optional[str] = None
) -> Tuple[pd.DataFrame, dict]:
    """
    Attempts to locate and load the DataFrame.
    Returns (df, metadata_dict).
    """
    meta = {"source": "unknown"}

    # 1. Try Person 3 storage by apply_job_id if provided
    if apply_job_id:
        p3_parquet = config.PERSON3_STORAGE_DIR / "applied" / f"{apply_job_id}.parquet"
        p3_json = config.PERSON3_STORAGE_DIR / "applied" / f"{apply_job_id}.json"
        if p3_parquet.exists():
            df = pd.read_parquet(p3_parquet)
            meta["source"] = f"person3_applied_parquet:{apply_job_id}"
            if p3_json.exists():
                try:
                    report_data = json.loads(p3_json.read_text())
                    meta["apply_report"] = report_data
                except Exception:
                    pass
            return df, meta

    # 2. Try Person 3 storage by dataset_id (glob matching)
    p3_applied_dir = config.PERSON3_STORAGE_DIR / "applied"
    if p3_applied_dir.exists():
        for p_file in p3_applied_dir.glob("*.parquet"):
            meta_file = p_file.with_suffix(".meta.json")
            if meta_file.exists():
                try:
                    meta_content = json.loads(meta_file.read_text())
                    if meta_content.get("dataset_id") == dataset_id:
                        df = pd.read_parquet(p_file)
                        meta["source"] = f"person3_dataset_id_match:{p_file.name}"
                        return df, meta
                except Exception:
                    pass

    # 3. Try Person 1 storage for raw/ingested dataset if Person 3 apply wasn't run
    p1_datasets_dir = config.PERSON1_STORAGE_DIR / "datasets"
    if p1_datasets_dir.exists():
        p1_parquet = p1_datasets_dir / f"{dataset_id}.parquet"
        p1_csv = p1_datasets_dir / f"{dataset_id}.csv"
        if p1_parquet.exists():
            df = pd.read_parquet(p1_parquet)
            meta["source"] = f"person1_parquet:{dataset_id}"
            return df, meta
        elif p1_csv.exists():
            df = pd.read_csv(p1_csv)
            meta["source"] = f"person1_csv:{dataset_id}"
            return df, meta

    # 4. Check person4 local storage or sample_data
    local_sample = config.BASE_DIR / "sample_data" / f"{dataset_id}.csv"
    if local_sample.exists():
        df = pd.read_csv(local_sample)
        meta["source"] = f"local_sample:{local_sample.name}"
        return df, meta

    raise FileNotFoundError(
        f"Unable to resolve dataset for dataset_id={dataset_id!r}, apply_job_id={apply_job_id!r}. "
        f"Checked Person 3 storage ({config.PERSON3_STORAGE_DIR}), Person 1 storage ({config.PERSON1_STORAGE_DIR}), "
        "and local storage."
    )
