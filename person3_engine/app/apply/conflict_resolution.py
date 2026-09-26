"""conflict_resolution.py — decides which of the *selected* suggestions can
actually be applied when two or more of them can't both apply to the same
column.

Two conflict rules, applied to the selected suggestion list before any
transform runs:

1. **Same-type collision**: two selected suggestions of the same `type`
   share a target column (e.g. two `scaling` suggestions both on 'age' — one
   asking for standard, one for robust). Only one scaling method can win, so
   the lower `priority_rank` (Person 2 ranks 1 = highest priority) is kept;
   the rest are marked `skipped_conflict`.

2. **Encoding-removes-column collision**: a selected `onehot` encoding
   suggestion replaces its target column entirely (see apply/encoding.py).
   Any *other selected suggestion whose pipeline stage runs after encoding*
   (scaling, transform, binning, interaction) and also targets that column
   can never run — the column won't exist by the time the pipeline reaches
   it — so it's marked `skipped_conflict`.

   Suggestions whose stage runs *before* encoding (imputation) are correctly
   left alone here: impute-then-encode is the standard, valid order, and
   flagging it as a "conflict" would block a perfectly normal combination —
   this was a real bug caught during live three-engine integration testing,
   where a legitimate `imputation` + `onehot encoding` pair on the same
   column was wrongly rejected.

`drop_redundant` is deliberately excluded from rule 2 entirely — it runs
last in the pipeline order, so anything else targeting a soon-to-be-dropped
column still gets to run first. That's wasted work, not a conflict.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.apply._stage_order import STAGE_ORDER

_ENCODING_STAGE = STAGE_ORDER["encoding"]


def resolve_conflicts(suggestions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (kept, skipped). `skipped` entries carry
    {suggestion_id, type, target_columns, reasoning} for the transformation log."""
    skipped: List[Dict[str, Any]] = []

    # --- Rule 1: same-type collisions ---
    by_type_column: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for s in suggestions:
        for col in s.get("target_columns", []):
            by_type_column[(s["type"], col)].append(s)

    losers_rule1: Dict[str, Dict[str, Any]] = {}
    for (_type, col), group in by_type_column.items():
        if len(group) <= 1:
            continue
        winner = min(group, key=lambda s: s.get("priority_rank", 0))
        for s in group:
            if s["id"] != winner["id"] and s["id"] not in losers_rule1:
                losers_rule1[s["id"]] = {
                    "suggestion_id": s["id"],
                    "type": s["type"],
                    "target_columns": s.get("target_columns", []),
                    "reasoning": (
                        f"Conflicts with '{winner['id']}' (both {s['type']} suggestions target "
                        f"'{col}'); '{winner['id']}' has higher priority (rank {winner.get('priority_rank', 0)} "
                        f"vs {s.get('priority_rank', 0)})."
                    ),
                }

    kept_after_rule1 = [s for s in suggestions if s["id"] not in losers_rule1]
    skipped.extend(losers_rule1.values())

    # --- Rule 2: onehot-encoding removes the column ---
    onehot_columns = {
        col
        for s in kept_after_rule1
        if s["type"] == "encoding" and s.get("params", {}).get("method") == "onehot"
        for col in s.get("target_columns", [])
    }

    losers_rule2: Dict[str, Dict[str, Any]] = {}
    kept: List[Dict[str, Any]] = []
    for s in kept_after_rule1:
        # drop_redundant runs last regardless — a soon-to-be-dropped column being
        # dropped by name still works even if it was also one-hot encoded away;
        # see module docstring on why that's not treated as a conflict here.
        runs_after_encoding = s["type"] != "drop_redundant" and STAGE_ORDER.get(s["type"], 0) > _ENCODING_STAGE
        if not runs_after_encoding:
            kept.append(s)
            continue
        clashing = onehot_columns.intersection(s.get("target_columns", []))
        if clashing:
            losers_rule2[s["id"]] = {
                "suggestion_id": s["id"],
                "type": s["type"],
                "target_columns": s.get("target_columns", []),
                "reasoning": (
                    f"Column(s) {sorted(clashing)} will be one-hot encoded away before this "
                    f"{s['type']} suggestion would run."
                ),
            }
        else:
            kept.append(s)

    skipped.extend(losers_rule2.values())
    return kept, skipped
