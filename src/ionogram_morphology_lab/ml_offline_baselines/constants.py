"""Contracts and policy constants for ML-C.1 offline baselines."""
from __future__ import annotations

OFFLINE_BASELINE_PROTOCOL_VERSION = "iml-ml-offline-baselines-0.1.0"
FEATURE_EXTRACTOR_VERSION = "iml-single-frame-pool16-0.1.0"
BASELINE_MAJORITY = "iml-majority-class-baseline-0.1.0"
BASELINE_NEAREST_CENTROID = "iml-nearest-centroid-pool16-0.1.0"
BASELINE_LOGISTIC = "iml-logistic-regression-pool16-0.1.0"
EXPERIMENT_DIRNAME = "model_lab/ml_c_baselines"
EXPERIMENT_STATES = frozenset(
    {"draft", "validated", "running", "completed", "failed", "cancelled", "archived"}
)
SUPPORTED_TASK = "spread_f_morphology_classification"
POOL_SIZE = 16
FEATURE_COUNT = 256
HOLDOUT_REFERENCE_FILENAME = "holdout_reference_labels.jsonl"

# Candidate, identity, split, and known leakage fields must not be model inputs.
FORBIDDEN_PREDICTOR_KEYS = frozenset(
    {
        "candidate", "candidate_id", "candidate_score", "candidate_label",
        "item_id", "identity_key", "project_id", "cohort_id", "cohort_revision",
        "source_inventory_id", "source_display_name", "source_sha256", "source_date",
        "frame_index", "frame_time", "sequence_id", "related_frame_group",
        "campaign_id", "acquisition_period", "atomic_group_id", "role",
        "target_label", "morphology", "assessability", "ambiguity", "interference",
        "contamination_state", "reviewer_role", "reviewer_alias",
    }
)

NO_CLAIM_STATEMENT_EN = (
    "ML-C.1 offline baselines are experimental development-only analyses, not "
    "independent validation. Holdout reference labels remain sealed."
)
NO_CLAIM_STATEMENT_RU = (
    "Офлайн-бейзлайны ML-C.1 — экспериментальный анализ только для разработки, "
    "а не независимая валидация. Эталонные метки holdout остаются запечатанными."
)
