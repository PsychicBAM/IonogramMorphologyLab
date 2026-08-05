"""Schema / contract versions for the morphology review corpus."""

from __future__ import annotations

REVIEW_CORPUS_SCHEMA_VERSION = 1
REVIEW_RECORD_SCHEMA_VERSION = 1
ADJUDICATION_SCHEMA_VERSION = 1
PROTOCOL_SCHEMA_VERSION = 1
COMMENT_RECORD_SCHEMA_VERSION = 1
COMMENT_TEMPLATE_VERSION = "iml-comment-template-0.1.0"
CORPUS_INTEGRITY_CONTRACT_VERSION = 1

# Reveal policies (frozen into protocol hash)
REVEAL_STRICT_COHORT = "strict_cohort_blinding"
REVEAL_PER_ITEM = "per_item_reveal"
# Legacy synonym treated as per-item reveal
REVEAL_AFTER_BLIND_LOCK = "after_blind_lock"

CORPORA_DIRNAME = "review_dataset/morphology_corpora"

PILOT_DESIGNATION_EN = "Pilot expert-review corpus — not a scientific validation set."
PILOT_DESIGNATION_RU = (
    "Пилотный корпус экспертной разметки — не является научно "
    "валидированным контрольным набором."
)

PROHIBITED_METRICS = frozenset(
    {
        "accuracy",
        "precision",
        "recall",
        "sensitivity",
        "specificity",
        "f1",
        "f1_score",
        "validated_performance",
    }
)
