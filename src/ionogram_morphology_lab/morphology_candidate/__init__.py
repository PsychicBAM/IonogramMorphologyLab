"""Shadow-only provisional morphology candidate engine (Phase 4C.1).

Never wires into production RuleEngine. Never claims scientific validation.
"""

from __future__ import annotations

from ionogram_morphology_lab.morphology_candidate.engine import (
    CANDIDATE_ENGINE_VERSION,
    evaluate_morphology_candidate,
)
from ionogram_morphology_lab.morphology_candidate.types import (
    CANDIDATE_CACHE_SCHEMA_VERSION,
    CANDIDATE_RESULT_CONTRACT_VERSION,
    EVIDENCE_LEDGER_SCHEMA_VERSION,
    MorphologyCandidateInput,
    MorphologyCandidateResult,
)

__all__ = [
    "CANDIDATE_ENGINE_VERSION",
    "CANDIDATE_CACHE_SCHEMA_VERSION",
    "EVIDENCE_LEDGER_SCHEMA_VERSION",
    "CANDIDATE_RESULT_CONTRACT_VERSION",
    "MorphologyCandidateInput",
    "MorphologyCandidateResult",
    "evaluate_morphology_candidate",
]
