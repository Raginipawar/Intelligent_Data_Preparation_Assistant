"""
missingness_rules.py — imputation suggestions, driven by Person 1's
`missingness` + `distributions` + `schema` sections of the Dataset Health Report.

Strategy choice isn't arbitrary:
  - numeric, |skew| > 1        -> median (robust to the long tail)
  - numeric, roughly symmetric -> mean
  - categorical, small gap     -> mode
  - categorical, large gap     -> explicit "missing" category (the gap itself may be
                                   informative — MNAR pattern — so don't paper over it)
  - boolean                    -> mode
  - datetime / text_freeform / unknown -> skipped; these need manual handling this
    engine won't guess at (imputing a "wrong" date or freeform string is worse than
    leaving it for a human).

Person 1's co-missingness pairs (Jaccard overlap of null-masks) are folded into the
reasoning string when relevant, since a high Jaccard overlap between two columns'
missingness is itself a signal (MNAR / structural gap) worth surfacing.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import suggestion_config as config
from app.suggestion_schemas import Suggestion, SuggestionType

_NUMERIC_DTYPES = {"numeric_int", "numeric_float"}


def _co_missing_partners(missingness: Dict[str, Any]) -> Dict[str, List[str]]:
    partners: Dict[str, List[str]] = {}
    for pair in missingness.get("co_missing_pairs", []) or []:
        c1, c2 = pair.get("col1"), pair.get("col2")
        jaccard = pair.get("jaccard", 0)
        if not c1 or not c2 or jaccard < 0.5:
            continue
        partners.setdefault(c1, []).append(c2)
        partners.setdefault(c2, []).append(c1)
    return partners


def build_imputation_suggestions(
    missingness: Dict[str, Any],
    distributions: Dict[str, Any],
    schema_columns: List[Dict[str, Any]],
) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    dtype_map = {c["name"]: c.get("inferred_dtype") for c in schema_columns}
    co_missing = _co_missing_partners(missingness)
    dist_columns = distributions.get("columns", {}) or {}

    for col, info in (missingness.get("columns", {}) or {}).items():
        pct = info.get("missing_pct") or 0.0
        if pct <= 0:
            continue

        dtype = dtype_map.get(col, "unknown")
        params: Dict[str, Any] = {}
        confidence = 0.7

        if dtype in _NUMERIC_DTYPES:
            skew = (dist_columns.get(col) or {}).get("skewness")
            if skew is not None and abs(skew) > 1:
                strategy = "median"
                reasoning = (
                    f"'{col}' is missing in {pct:.1f}% of rows. Median imputation is suggested "
                    f"because the column is skewed (skewness={skew:.2f}) — the mean would be pulled "
                    "toward the long tail and misrepresent a 'typical' value."
                )
                confidence = 0.8
            else:
                strategy = "mean"
                reasoning = (
                    f"'{col}' is missing in {pct:.1f}% of rows. The distribution is roughly symmetric"
                    + (f" (skewness={skew:.2f})" if skew is not None else "")
                    + ", so mean imputation is a safe default."
                )
            params = {"strategy": strategy}

        elif dtype == "categorical":
            if pct < config.LOW_MISSING_MODE_PCT:
                params = {"strategy": "mode"}
                reasoning = (
                    f"'{col}' is missing in only {pct:.1f}% of rows — small enough that filling with "
                    "the most frequent category (mode) is unlikely to distort the distribution."
                )
                confidence = 0.75
            else:
                params = {"strategy": "constant", "fill_value": "missing"}
                reasoning = (
                    f"'{col}' is missing in {pct:.1f}% of rows — large enough that the missingness "
                    "itself may be informative (MNAR). Suggest filling with an explicit 'missing' "
                    "category instead of the mode, so the model can learn from the gap rather than "
                    "have it silently absorbed into the majority class."
                )
                confidence = 0.65

        elif dtype == "boolean":
            params = {"strategy": "mode"}
            reasoning = f"'{col}' (boolean) is missing in {pct:.1f}% of rows; mode imputation is the simplest safe default for a two-valued column."
            confidence = 0.7

        else:
            continue  # datetime / text_freeform / unknown — needs manual handling

        partners = co_missing.get(col)
        if partners:
            reasoning += (
                f" Note: missingness in '{col}' co-occurs with {partners} (Jaccard overlap >= 0.5 per "
                "Person 1's analysis), suggesting a structural/MNAR pattern — consider adding a "
                "missingness-indicator feature alongside this imputation, not just the fill itself."
            )

        if pct >= config.HIGH_MISSING_REVIEW_PCT:
            reasoning += (
                f" At {pct:.1f}% missing, also consider dropping this column entirely if imputation "
                "doesn't meaningfully help downstream model performance."
            )
            confidence = min(confidence, 0.5)

        impact = "high" if pct > 20 else "medium" if pct > 5 else "low"
        suggestions.append(
            Suggestion(
                id="placeholder",
                type=SuggestionType.IMPUTATION,
                target_columns=[col],
                reasoning=reasoning,
                expected_impact=f"{impact} — fills a {pct:.1f}% gap in '{col}'",
                params=params,
                confidence=round(confidence, 3),
            )
        )

    return suggestions
