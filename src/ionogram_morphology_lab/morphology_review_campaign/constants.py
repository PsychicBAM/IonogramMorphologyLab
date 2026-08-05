"""Pilot expert-review campaign contracts (Phase 4C.3)."""

from __future__ import annotations

CAMPAIGN_SCHEMA_VERSION = 1
CAMPAIGN_PROTOCOL_SCHEMA_VERSION = 1
CAMPAIGN_INTEGRITY_CONTRACT_VERSION = 1

CAMPAIGNS_DIRNAME = "review_dataset/morphology_campaigns"

CAMPAIGN_DESIGNATION_EN = (
    "Pilot expert-review campaign — not a scientific validation study."
)
CAMPAIGN_DESIGNATION_RU = (
    "Пилотная кампания экспертной оценки — не является научной валидацией."
)

CAMPAIGN_STATES = frozenset(
    {"draft", "ready", "active", "paused", "completed", "archived"}
)

COHORT_ROLES = frozenset(
    {
        "first_review",
        "second_review",
        "holdout_descriptive",
        "adjudication_subset",
    }
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

BUILD_IDENTITY_DEFAULT = "4C.4a"
