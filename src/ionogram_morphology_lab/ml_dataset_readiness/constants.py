"""Schema / contract versions for ML-A.1 dataset readiness audit."""

from __future__ import annotations

READINESS_PROTOCOL_VERSION = "iml-ml-dataset-readiness-0.1.0"
READINESS_MANIFEST_SCHEMA_VERSION = 1
READINESS_INVENTORY_SCHEMA_VERSION = 1
READINESS_GATE_SCHEMA_VERSION = 1
HOLDOUT_FEASIBILITY_SCHEMA_VERSION = 1

READINESS_DIRNAME = "review_dataset/ml_readiness"

LIFECYCLE_STATES = frozenset(
    {
        "draft",
        "frozen",
        "reviewed",
        "gate_recorded",
        "archived",
    }
)

TASK_CONTRACTS = frozenset(
    {
        "spread_f_morphology_classification",
        "assessability_quality_classification",
        "interference_classification",
        "ionogram_parameter_scaling",
    }
)

CONTAMINATION_STATES = frozenset(
    {
        "untouched_candidate",
        "development_exposed",
        "future_training_exposed",
        "holdout_reserved",
        "holdout_revealed",
        "prohibited_invalid",
    }
)

MISSINGNESS_CATEGORIES = frozenset(
    {
        "structurally_missing",
        "not_applicable",
        "expert_abstained",
        "unavailable_data",
        "corrupted_identity",
    }
)

GATE_OUTCOMES = frozenset(
    {
        "A_collect_more_expert_labels",
        "B_repair_label_contract_or_missing_data",
        "C_expand_class_source_date_sequence_coverage",
        "D_obtain_independent_expert_review",
        "E_untouched_holdout_not_currently_feasible",
        "F_ready_for_mlb_manifest_planning_only",
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
        "ground_truth",
        "confusion_matrix",
        "error_matrix",
        "accuracy_matrix",
        "inter_rater_kappa",
    }
)

ADJACENT_FRAME_WARNING_EN = (
    "Adjacent frames may represent the same physical event and are not fully "
    "independent observations."
)
ADJACENT_FRAME_WARNING_RU = (
    "Соседние кадры могут отражать одно и то же физическое событие и не "
    "являются полностью независимыми наблюдениями."
)

LIMITED_COVERAGE_WARNING_EN = (
    "Limited coverage — insufficient to decide on preparing an ML dataset "
    "without additional expert labelling."
)
LIMITED_COVERAGE_WARNING_RU = (
    "Ограниченное покрытие — недостаточно для решения о подготовке ML-набора "
    "без дополнительной экспертной разметки."
)

NO_CLAIM_STATEMENT_EN = (
    "ML-A.1a.2 dataset readiness audit — descriptive inventory only. "
    "Not scientific validation. Not ground truth. No accuracy/F1 claims. "
    "No model training authorized. Outcome F authorizes ML-B manifest "
    "planning only."
)
NO_CLAIM_STATEMENT_RU = (
    "Аудит готовности данных ML-A.1a.2 — только описательная инвентаризация. "
    "Не научная валидация. Не ground truth. Без заявлений accuracy/F1. "
    "Обучение моделей не разрешено. Исход F разрешает только планирование "
    "манифестов ML-B."
)

PARAMETER_SCALING_UNSUPPORTED_EN = (
    "Unsupported by current labels — no ionogram parameter scaling labels available"
)
PARAMETER_SCALING_UNSUPPORTED_RU = (
    "Не поддерживается текущими метками — метки масштабирования параметров отсутствуют"
)
