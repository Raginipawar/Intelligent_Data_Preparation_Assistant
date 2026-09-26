"""
dataset_client.py — resolves the one required input this engine cannot do
without: the raw dataset as a pandas DataFrame.

Resolution order for `dataset_id`:
  a) This engine's own `storage/datasets/{dataset_id}.parquet` — written by
     this engine's own POST /upload (added purely for standalone testing/dev,
     so Person 3 never has to have Person 1's engine running).
  b) Person 1's shared storage on disk (config.PERSON1_DATASETS_DIR /
     f"{dataset_id}.parquet") — convenience path for local, co-located dev,
     same pattern Person 2's health_report_client.try_load_raw_dataset uses.

Unlike Person 2's raw-dataset lookup (which is optional, enrichment-only),
the raw dataset is *required* here — /apply cannot do anything without it —
so failure to resolve raises `DatasetUnavailable` instead of degrading.

Also resolves the original upload's `source_type` (single CSV vs ZIP, etc.)
from whichever engine's ingestion metadata is found, so POST /export can
default to matching the format the user originally uploaded.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from app import apply_config as config


class DatasetUnavailable(Exception):
    """Raised when the raw dataset could not be resolved from any source."""


def _own_dataset_path(dataset_id: str) -> Path:
    return config.DATASETS_DIR / f"{dataset_id}.parquet"


def _own_meta_path(dataset_id: str) -> Path:
    return config.DATASETS_DIR / f"{dataset_id}.meta.json"


def _person1_dataset_path(dataset_id: str) -> Path:
    return config.PERSON1_DATASETS_DIR / f"{dataset_id}.parquet"


def _person1_meta_path(dataset_id: str) -> Path:
    return config.PERSON1_DATASETS_DIR / f"{dataset_id}.meta.json"


def store_own_dataset(df: pd.DataFrame, source_type: str, primary_file: str) -> str:
    """Used by this engine's own POST /upload. Returns a new dataset_id."""
    dataset_id = str(uuid.uuid4())
    df.to_parquet(_own_dataset_path(dataset_id), index=True)
    _own_meta_path(dataset_id).write_text(
        json.dumps(
            {"dataset_id": dataset_id, "source_type": source_type, "primary_file": primary_file},
            indent=2,
        )
    )
    return dataset_id


def resolve_dataset(dataset_id: str) -> Tuple[pd.DataFrame, str, Optional[str]]:
    """Returns (df, source_type, primary_file). Raises DatasetUnavailable if
    dataset_id isn't found in either this engine's own storage or Person 1's."""
    own_path = _own_dataset_path(dataset_id)
    if own_path.exists():
        df = pd.read_parquet(own_path)
        source_type, primary_file = "single_csv", None
        meta_path = _own_meta_path(dataset_id)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            source_type = meta.get("source_type", source_type)
            primary_file = meta.get("primary_file")
        return df, source_type, primary_file

    p1_path = _person1_dataset_path(dataset_id)
    if p1_path.exists():
        df = pd.read_parquet(p1_path)
        source_type, primary_file = "single_csv", None
        meta_path = _person1_meta_path(dataset_id)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            ingestion = meta.get("ingestion", {})
            source_type = ingestion.get("source_type", source_type)
            primary_file = ingestion.get("primary_file")
        return df, source_type, primary_file

    raise DatasetUnavailable(
        f"No dataset found for dataset_id={dataset_id!r}. Checked this engine's own "
        f"storage ({config.DATASETS_DIR}) and Person 1's co-located storage "
        f"({config.PERSON1_DATASETS_DIR}). Call this engine's own POST /upload first, "
        "or make sure Person 1's engine's storage is reachable at PERSON1_STORAGE_DIR."
    )
