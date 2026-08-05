"""Expert Morphology Review Corpus (Phase 4C.2) — blind review, not ground truth.

Project-scoped under ``{project}/review_dataset/morphology_corpora/<cohort_id>/``.
Distinct from geometry reviews and from the app-root owner ``review_dataset`` labels.
"""

from __future__ import annotations

from ionogram_morphology_lab.morphology_review_corpus.constants import (
    ADJUDICATION_SCHEMA_VERSION,
    CORPUS_INTEGRITY_CONTRACT_VERSION,
    PROTOCOL_SCHEMA_VERSION,
    REVIEW_CORPUS_SCHEMA_VERSION,
    REVIEW_RECORD_SCHEMA_VERSION,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    HUMAN_MORPHOLOGY_CODES,
    morphology_label,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

__all__ = [
    "ADJUDICATION_SCHEMA_VERSION",
    "CORPUS_INTEGRITY_CONTRACT_VERSION",
    "HUMAN_MORPHOLOGY_CODES",
    "MorphologyReviewCorpusStore",
    "PROTOCOL_SCHEMA_VERSION",
    "REVIEW_CORPUS_SCHEMA_VERSION",
    "REVIEW_RECORD_SCHEMA_VERSION",
    "morphology_label",
]
