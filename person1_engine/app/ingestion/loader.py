"""
loader.py — turns an uploaded file (CSV or ZIP) into a single working
pandas DataFrame plus an IngestionSummary describing exactly how it got there.
"""
from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from charset_normalizer import from_bytes

from app.schemas import SourceType

COMMON_DELIMITERS = [",", ";", "\t", "|"]


@dataclass
class LoadResult:
    df: pd.DataFrame
    source_type: SourceType
    primary_file: str
    supporting_files: List[Dict] = field(default_factory=list)
    encoding: str = "utf-8"
    encoding_confidence: float = 1.0
    delimiter: str = ","
    malformed_rows_skipped: int = 0
    warnings: List[str] = field(default_factory=list)


def detect_encoding(raw: bytes) -> Tuple[str, float]:
    """Best-effort encoding detection. Falls back to utf-8 if detection
    itself fails (e.g. empty file) rather than raising."""
    try:
        best = from_bytes(raw).best()
        if best is not None:
            return best.encoding, round(1.0 - best.chaos, 3)
    except Exception:
        pass
    return "utf-8", 0.5


def detect_delimiter(sample_text: str) -> str:
    """csv.Sniffer first, falling back to a frequency count over common
    delimiters if the sniffer can't decide (short files, single column, etc.)."""
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters="".join(COMMON_DELIMITERS))
        return dialect.delimiter
    except csv.Error:
        pass
    first_line = sample_text.splitlines()[0] if sample_text.splitlines() else ""
    counts = {d: first_line.count(d) for d in COMMON_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def _read_csv_bytes(raw: bytes, filename: str) -> Tuple[pd.DataFrame, str, float, str, int, List[str]]:
    """Parse raw CSV bytes robustly: detect encoding + delimiter, tolerate
    malformed rows (counting rather than silently dropping them), keep going
    even if some rows are broken instead of failing the whole upload."""
    warnings: List[str] = []
    encoding, enc_confidence = detect_encoding(raw)

    try:
        text_sample = raw[:65536].decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        encoding = "utf-8"
        text_sample = raw[:65536].decode(encoding, errors="replace")
        warnings.append(f"Encoding detection failed for {filename}; fell back to utf-8 with replacement chars.")

    delimiter = detect_delimiter(text_sample)

    bad_lines: List[str] = []

    def _capture_bad_line(bad_line: List[str]) -> Optional[List[str]]:
        bad_lines.append(bad_line)
        return None  # tell pandas to drop it

    try:
        df = pd.read_csv(
            io.BytesIO(raw),
            encoding=encoding,
            sep=delimiter,
            engine="python",
            on_bad_lines=_capture_bad_line,
        )
    except Exception as exc:
        # Last-resort fallback: let pandas guess everything.
        warnings.append(f"Strict parse of {filename} failed ({exc}); retrying with pandas defaults.")
        df = pd.read_csv(io.BytesIO(raw), encoding=encoding, sep=None, engine="python", on_bad_lines="skip")

    if bad_lines:
        warnings.append(f"{len(bad_lines)} malformed row(s) skipped while parsing {filename}.")

    return df, encoding, enc_confidence, delimiter, len(bad_lines), warnings


def _find_join_keys(frames: Dict[str, pd.DataFrame]) -> Optional[str]:
    """Heuristic: if every CSV in the zip shares one column name that looks
    like a key (high uniqueness in at least one frame), suggest joining on it."""
    if len(frames) < 2:
        return None
    common_cols = set.intersection(*(set(df.columns) for df in frames.values()))
    id_like = [c for c in common_cols if any(tok in c.lower() for tok in ("id", "key", "code"))]
    candidates = id_like or list(common_cols)
    for col in candidates:
        if all(col in df.columns and df[col].nunique() > 0 for df in frames.values()):
            return col
    return None


def load_upload(raw_bytes: bytes, filename: str) -> LoadResult:
    """Entry point: accept raw bytes of an uploaded CSV or ZIP and return a
    single working DataFrame + a full account of how it was produced."""
    is_zip = filename.lower().endswith(".zip") or zipfile.is_zipfile(io.BytesIO(raw_bytes))

    if not is_zip:
        df, encoding, enc_conf, delim, n_bad, warns = _read_csv_bytes(raw_bytes, filename)
        return LoadResult(
            df=df,
            source_type=SourceType.SINGLE_CSV,
            primary_file=filename,
            encoding=encoding,
            encoding_confidence=enc_conf,
            delimiter=delim,
            malformed_rows_skipped=n_bad,
            warnings=warns,
        )

    # ZIP path: inspect every member, parse every CSV, decide single/multi/supporting.
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/") and not n.startswith("__MACOSX")]
        csv_names = [n for n in names if n.lower().endswith(".csv")]
        other_names = [n for n in names if not n.lower().endswith(".csv")]

        if not csv_names:
            raise ValueError("ZIP contains no CSV files — nothing to ingest.")

        parsed: Dict[str, pd.DataFrame] = {}
        meta: Dict[str, Dict] = {}
        all_warnings: List[str] = []
        total_bad = 0
        last_encoding, last_delim, last_conf = "utf-8", ",", 1.0

        for name in csv_names:
            raw = zf.read(name)
            df, encoding, enc_conf, delim, n_bad, warns = _read_csv_bytes(raw, name)
            parsed[name] = df
            meta[name] = {"rows": len(df), "columns": list(df.columns)}
            all_warnings.extend(warns)
            total_bad += n_bad
            last_encoding, last_delim, last_conf = encoding, delim, enc_conf

        supporting_meta = [{"name": n, "size_bytes": zf.getinfo(n).file_size} for n in other_names]

        if len(parsed) == 1:
            name, df = next(iter(parsed.items()))
            source_type = (
                SourceType.ZIP_SINGLE_CSV if not other_names else SourceType.ZIP_MULTI_CSV_WITH_SUPPORTING
            )
            return LoadResult(
                df=df,
                source_type=source_type,
                primary_file=name,
                supporting_files=supporting_meta,
                encoding=last_encoding,
                encoding_confidence=last_conf,
                delimiter=last_delim,
                malformed_rows_skipped=total_bad,
                warnings=all_warnings,
            )

        # Multiple CSVs: try a heuristic join; else fall back to "largest table is primary".
        join_key = _find_join_keys(parsed)
        if join_key:
            merged = None
            for name, df in parsed.items():
                merged = df if merged is None else merged.merge(df, on=join_key, how="outer", suffixes=("", f"__{name}"))
            all_warnings.append(f"Joined {len(parsed)} CSVs on shared key column '{join_key}'.")
            return LoadResult(
                df=merged,
                source_type=SourceType.ZIP_MULTI_CSV_JOINED,
                primary_file="+".join(parsed.keys()),
                supporting_files=supporting_meta + [{"joined_on": join_key}],
                encoding=last_encoding,
                encoding_confidence=last_conf,
                delimiter=last_delim,
                malformed_rows_skipped=total_bad,
                warnings=all_warnings,
            )

        primary_name = max(parsed, key=lambda n: len(parsed[n]))
        other_csvs_meta = [{"name": n, **meta[n]} for n in parsed if n != primary_name]
        all_warnings.append(
            f"No shared join key found across {len(parsed)} CSVs; treating '{primary_name}' "
            f"(largest, {len(parsed[primary_name])} rows) as the primary dataset and the rest as supporting files."
        )
        return LoadResult(
            df=parsed[primary_name],
            source_type=SourceType.ZIP_MULTI_CSV_WITH_SUPPORTING,
            primary_file=primary_name,
            supporting_files=supporting_meta + other_csvs_meta,
            encoding=last_encoding,
            encoding_confidence=last_conf,
            delimiter=last_delim,
            malformed_rows_skipped=total_bad,
            warnings=all_warnings,
        )
