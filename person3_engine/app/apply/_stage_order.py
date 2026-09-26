"""_stage_order.py — the one place the pipeline's stage ordering lives, shared
by orchestrator.py (to actually sequence application) and
conflict_resolution.py (to know whether a suggestion runs before or after an
onehot encoding that removes its target column — see conflict_resolution.py's
rule 2 for why this matters: a suggestion that runs *earlier* in the pipeline
isn't actually blocked by a later encoding step)."""
from __future__ import annotations

STAGE_ORDER = {
    "imputation": 0,
    "encoding": 1,
    "scaling": 2,
    "transform": 3,
    "binning": 4,
    "interaction": 5,
    "drop_redundant": 6,
}
