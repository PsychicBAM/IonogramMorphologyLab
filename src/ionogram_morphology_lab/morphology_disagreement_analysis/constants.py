"""Schema / contract versions for disagreement analysis (Phase 4C.4a)."""

from __future__ import annotations

ANALYSIS_PROTOCOL_VERSION = "iml-disagreement-analysis-0.1.0"
ANALYSIS_MANIFEST_SCHEMA_VERSION = 1
ANALYSIS_SNAPSHOT_SCHEMA_VERSION = 1
DECISION_GATE_SCHEMA_VERSION = 1
HOLDOUT_PLAN_SCHEMA_VERSION = 1
CONTAMINATION_SCHEMA_VERSION = 1
ANALYST_NOTE_SCHEMA_VERSION = 1

ANALYSES_DIRNAME = "review_dataset/morphology_analyses"

LIFECYCLE_STATES = frozenset(
    {
        "draft",
        "frozen",
        "reviewed",
        "decision_recorded",
        "archived",
    }
)

EXCLUSION_REASONS = frozenset(
    {
        "eligible_comparable",
        "expert_abstention",
        "candidate_abstention",
        "both_abstained",
        "non_comparable",
        "unavailable_candidate",
        "unavailable_source",
        "invalid_identity",
        "unresolved_revision",
        "blind_not_revealed",
        "missing_current_comparison",
        "missing_locked_review",
        "incompatible_candidate_version",
    }
)

HYPOTHESIS_CATEGORIES = frozenset(
    {
        "label_definition_ambiguity",
        "assessability_limitation",
        "interference_related",
        "possible_upstream_geometry_issue",
        "possible_evidence_extraction_issue",
        "possible_candidate_ruleset_issue",
        "source_data_issue",
        "insufficient_information",
        "other",
    }
)

HYPOTHESIS_CONFIDENCE = frozenset({"low", "medium", "high"})

DECISION_OUTCOMES = frozenset(
    {
        "A_insufficient_evidence",
        "B_no_candidate_change",
        "C_documentation_or_label_clarification",
        "D_data_assessability_interference_investigation",
        "E_upstream_geometry_evidence_investigation",
        "F_candidate_ruleset_hypothesis_justified",
    }
)

SMALL_SAMPLE_THRESHOLD = 10

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
    }
)

PILOT_DESIGNATION_EN = (
    "Pilot disagreement analysis — descriptive only; not scientific validation."
)
PILOT_DESIGNATION_RU = (
    "Пилотный анализ расхождений — только описательный; "
    "не является научной валидацией."
)
