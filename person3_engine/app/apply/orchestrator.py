"""orchestrator.py — glues every apply/* module together into the one thing
Person 3's job-queue entry point (apply_pipeline.py) needs: given a raw
DataFrame, the full suggestion list, and the user's selected subset, produce
the final cleaned DataFrame + a complete, ordered transformation log.

Pipeline stages, applied in Person 2's documented order (imputation ->
encoding -> scaling -> transform -> binning -> interaction -> drop_redundant),
with conflict resolution run first and budget-constrained feature selection
run last:

  1. Filter to selected_suggestion_ids (unknown ids logged, not applied)
  2. Resolve conflicts among the selected suggestions (conflict_resolution.py)
  3. Apply survivors in pipeline-stage order, each wrapped so a single bad
     suggestion (missing column, bad params) can't take down the whole run
  4. Trim to feature_budget if set (feature_selection.py)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.apply._stage_order import STAGE_ORDER
from app.apply.binning import apply_binning
from app.apply.conflict_resolution import resolve_conflicts
from app.apply.drop_redundant import apply_drop_redundant
from app.apply.encoding import apply_encoding
from app.apply.feature_selection import apply_feature_budget
from app.apply.imputation import apply_imputation
from app.apply.interaction import apply_interaction
from app.apply.scaling import apply_scaling
from app.apply.transform import apply_transform

# Tier assigned to newly-added columns based on the suggestion type that
# created them — consumed by feature_selection.py's budget trimming.
_NEW_COLUMN_TIER = {
    "interaction": 3,
    "binning": 2,
    "encoding": 1,  # only onehot actually adds columns; frequency/target modify in place
}


def _dispatch(suggestion: Dict[str, Any], df: pd.DataFrame, target_col: Optional[str]) -> Tuple[pd.DataFrame, str]:
    stype = suggestion["type"]
    if stype == "imputation":
        return apply_imputation(df, suggestion)
    if stype == "encoding":
        return apply_encoding(df, suggestion, target_col=target_col)
    if stype == "scaling":
        return apply_scaling(df, suggestion)
    if stype == "transform":
        return apply_transform(df, suggestion)
    if stype == "binning":
        return apply_binning(df, suggestion)
    if stype == "interaction":
        return apply_interaction(df, suggestion)
    if stype == "drop_redundant":
        return apply_drop_redundant(df, suggestion)
    raise ValueError(f"Unknown suggestion type {stype!r}")


def run_orchestration(
    df: pd.DataFrame,
    all_suggestions: List[Dict[str, Any]],
    selected_suggestion_ids: List[str],
    feature_budget: Optional[int] = None,
    target_col: Optional[str] = None,
) -> Dict[str, Any]:
    df = df.copy()
    by_id = {s["id"]: s for s in all_suggestions}

    log: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    applied_ids: List[str] = []
    column_registry: Dict[str, Dict[str, Any]] = {}

    def _next_order() -> int:
        return len(log) + 1

    # --- not-selected suggestions: recorded for transparency, never processed ---
    selected_set = set(selected_suggestion_ids)
    for s in all_suggestions:
        if s["id"] not in selected_set:
            skipped.append(
                {
                    "suggestion_id": s["id"],
                    "type": s["type"],
                    "target_columns": s.get("target_columns", []),
                    "reasoning": "Not in selected_suggestion_ids.",
                    "status": "skipped_not_selected",
                }
            )

    # --- unknown ids in the selection ---
    selected: List[Dict[str, Any]] = []
    for sid in selected_suggestion_ids:
        s = by_id.get(sid)
        if s is None:
            entry = {
                "suggestion_id": sid,
                "type": None,
                "target_columns": [],
                "reasoning": "Suggestion id not found in the provided suggestion list.",
                "status": "skipped_error",
            }
            log.append({"order": _next_order(), **{k: v for k, v in entry.items() if k != "status"},
                        "action": "not applied", "status": entry["status"]})
            skipped.append(entry)
            continue
        selected.append(s)

    # --- conflict resolution ---
    kept, conflict_skips = resolve_conflicts(selected)
    for c in conflict_skips:
        c["status"] = "skipped_conflict"
        log.append({"order": _next_order(), "suggestion_id": c["suggestion_id"], "type": c["type"],
                     "target_columns": c["target_columns"], "action": "not applied",
                     "reasoning": c["reasoning"], "status": "skipped_conflict"})
    skipped.extend(conflict_skips)

    # --- apply survivors in pipeline-stage order ---
    ordered = sorted(kept, key=lambda s: (STAGE_ORDER.get(s["type"], 99), s.get("priority_rank", 0)))

    for s in ordered:
        missing = [c for c in s.get("target_columns", []) if c not in df.columns]
        if missing:
            entry = {
                "suggestion_id": s["id"], "type": s["type"], "target_columns": s.get("target_columns", []),
                "reasoning": f"Column(s) {missing} not present in the dataset at this point in the pipeline.",
                "status": "skipped_missing_column",
            }
            log.append({"order": _next_order(), **{k: v for k, v in entry.items() if k != "status"},
                        "action": "not applied", "status": entry["status"]})
            skipped.append(entry)
            continue

        before_cols = set(df.columns)
        try:
            df, action = _dispatch(s, df, target_col)
        except Exception as exc:  # noqa: BLE001 — one bad suggestion shouldn't kill the run
            entry = {
                "suggestion_id": s["id"], "type": s["type"], "target_columns": s.get("target_columns", []),
                "reasoning": f"Error applying suggestion: {exc}", "status": "skipped_error",
            }
            log.append({"order": _next_order(), **{k: v for k, v in entry.items() if k != "status"},
                        "action": "not applied", "status": entry["status"]})
            skipped.append(entry)
            continue

        applied_ids.append(s["id"])
        log.append({
            "order": _next_order(), "suggestion_id": s["id"], "type": s["type"],
            "target_columns": s.get("target_columns", []), "action": action,
            "reasoning": s.get("reasoning", ""), "status": "applied",
        })

        tier = _NEW_COLUMN_TIER.get(s["type"])
        if tier:
            for new_col in set(df.columns) - before_cols:
                column_registry[new_col] = {
                    "tier": tier, "confidence": s.get("confidence", 0.5), "source_suggestion_id": s["id"],
                }

    # --- budget-constrained feature selection ---
    df, budget_entries = apply_feature_budget(df, column_registry, feature_budget)
    for entry in budget_entries:
        log.append({
            "order": _next_order(), "suggestion_id": None, "type": "feature_budget",
            "target_columns": [entry["column"]] if entry["column"] else [],
            "action": "dropped" if entry["column"] else "budget not fully satisfied",
            "reasoning": entry["reasoning"], "status": "budget_drop",
        })

    return {
        "df": df,
        "transformation_log": log,
        "applied_suggestions": applied_ids,
        "skipped_suggestions": skipped,
    }
