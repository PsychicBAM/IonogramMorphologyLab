"""Schema / contract versions for ML-B.1 immutable dataset manifests."""

from __future__ import annotations

MANIFEST_PROTOCOL_VERSION = "iml-ml-dataset-manifests-0.1.0"
MANIFEST_SET_SCHEMA_VERSION = 1
SPLIT_POLICY_VERSION = "iml-ml-split-policy-0.1.0"
MANIFEST_DIRNAME = "review_dataset/ml_manifests"

LIFECYCLE_STATES = frozenset({"draft", "validated", "frozen", "archived"})

DATASET_ROLES = frozenset(
    {"train", "development", "untouched_holdout", "excluded"}
)

GROUPING_POLICIES = frozenset(
    {
        "sequence_blocked",
        "related_frame_group_blocked",
        "source_date_blocked",
        "acquisition_period_blocked",
        "campaign_blocked",
        "conservative_combined_leakage_graph",
        "manual_atomic_group_assignment",
    }
)

DEFAULT_GROUPING_POLICY = "conservative_combined_leakage_graph"

# Reuse ML-A task contracts by importing from readiness; listed for docs/tests.
from ionogram_morphology_lab.ml_dataset_readiness.constants import (  # noqa: E402
    CONTAMINATION_STATES,
    GATE_OUTCOMES,
    PROHIBITED_METRICS,
    TASK_CONTRACTS,
)

GATE_F = "F_ready_for_mlb_manifest_planning_only"

NO_CLAIM_STATEMENT_EN = (
    "ML-B.1 dataset manifests — immutable identity and role reservation only. "
    "Not scientific validation. Not ground truth. No accuracy/F1 claims. "
    "No model training authorized. Holdout reference labels are workflow-sealed, "
    "not cryptographically secret. ML-C is not started."
)
NO_CLAIM_STATEMENT_RU = (
    "Манифесты наборов данных ML-B.1 — только неизменяемые идентичности и "
    "резервирование ролей. Не научная валидация. Не ground truth. Без заявлений "
    "accuracy/F1. Обучение моделей не разрешено. Эталонные метки holdout "
    "запечатаны рабочим процессом, а не криптографически. ML-C не начат."
)

WORKFLOW_SEAL_NOTE_EN = (
    "Holdout reference-label sealing is a workflow control, not cryptographic security."
)
WORKFLOW_SEAL_NOTE_RU = (
    "Запечатывание эталонных меток holdout — контроль рабочего процесса, "
    "а не криптографическая защита."
)

HOLDOUT_UNLOCK_FORBIDDEN_EN = (
    "ML-B cannot unlock holdout reference labels. Unlock requires a future ML-E protocol."
)
HOLDOUT_UNLOCK_FORBIDDEN_RU = (
    "ML-B не может разблокировать эталонные метки holdout. Разблокировка "
    "требует будущего протокола ML-E."
)
