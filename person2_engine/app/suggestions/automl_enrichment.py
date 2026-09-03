"""
automl_enrichment.py — the "real AutoML library" layer called for in the project
spec, kept strictly optional/corroborating rather than authoritative — mirroring
Person 1's own design philosophy (Isolation Forest primary + naive distance
baseline for comparison; LightGBM explicitly labeled "rough, not authoritative").

Two libraries, two different stories:

- AutoGluon (`autogluon.features`): we use just its
  `AutoMLPipelineFeatureGenerator` — NOT a full TabularPredictor.fit(), which
  would mean training a whole model ensemble just to get preprocessing opinions.
  The feature generator alone reveals what AutoGluon would do per column
  (keep/drop/retype) in seconds. Requires the raw dataframe, which is why
  suggestion_builder.py only calls this when Person 1's dataset happens to be
  reachable (see health_report_client.try_load_raw_dataset) — it is never a
  hard requirement for the rule-based suggestions above.

- auto-sklearn: does not ship Windows wheels at all (depends on pyrfr/SMAC,
  POSIX-only), and even on Linux/macOS a real run is a multi-minute
  hyperparameter search — far too slow to run synchronously inside /suggest.
  So this reports *why* it's skipped rather than attempting a fit, which is
  more honest than pretending to run it and silently no-op'ing.
"""
from __future__ import annotations

import platform
from typing import Any, Dict, Optional

import pandas as pd


def run_autogluon_feature_enrichment(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if df is None:
        return {
            "ran": False,
            "note": (
                "No raw dataset was reachable by this service (only the health report JSON was "
                "available). AutoGluon enrichment skipped; rule-based suggestions above are unaffected."
            ),
        }

    try:
        from autogluon.features.generators import AutoMLPipelineFeatureGenerator
    except ImportError:
        return {
            "ran": False,
            "note": (
                "autogluon.features is not installed. Run `pip install autogluon.features` to enable "
                "this enrichment layer. Rule-based suggestions above are unaffected."
            ),
        }

    try:
        generator = AutoMLPipelineFeatureGenerator()
        transformed = generator.fit_transform(df.copy())
        dropped = [c for c in df.columns if c not in transformed.columns]
        feature_type_map = getattr(generator, "feature_type_map", None) or {}
        return {
            "ran": True,
            "n_features_in": int(df.shape[1]),
            "n_features_out": int(transformed.shape[1]),
            "columns_dropped_by_autogluon": dropped,
            "feature_type_map": {k: str(v) for k, v in feature_type_map.items()},
            "note": (
                "AutoGluon's feature generator independently decided a type/keep-or-drop treatment "
                "for each column. Used here only to corroborate the rule-based suggestions above, not "
                "to replace them."
            ),
        }
    except Exception as exc:  # noqa: BLE001 — enrichment must never break /suggest
        return {"ran": False, "note": f"AutoGluon feature generator raised an error and was skipped: {exc}"}


def try_auto_sklearn_peek() -> Dict[str, Any]:
    if platform.system() == "Windows":
        return {
            "ran": False,
            "note": (
                "auto-sklearn does not support Windows (it depends on pyrfr/SMAC, which ship no "
                "Windows wheels) — skipped. AutoGluon's feature generator above stands in as the "
                "AutoML corroboration layer on this platform."
            ),
        }
    try:
        import autosklearn  # noqa: F401
    except ImportError:
        return {
            "ran": False,
            "note": "auto-sklearn is not installed. Install it on a Linux/macOS environment to enable this optional layer.",
        }
    return {
        "ran": False,
        "note": (
            "auto-sklearn is installed and importable, but a full search takes minutes and is too "
            "slow to run synchronously inside /suggest. Wire it into an offline batch job if you want "
            "its model-search preprocessing choices as a periodic cross-check."
        ),
    }
