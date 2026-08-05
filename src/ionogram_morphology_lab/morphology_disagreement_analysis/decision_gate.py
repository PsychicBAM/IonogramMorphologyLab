"""Ruleset Decision Gate — formal descriptive outcomes only."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_disagreement_analysis.analytics import (
    descriptive_dashboard,
    dominant_transitions,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    DECISION_OUTCOMES,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    AnalysisManifest,
    DecisionGateRecord,
    HoldoutPlan,
    SnapshotItemRecord,
)


REQUIRED_DECISION_FIELDS = (
    "outcome",
    "snapshot_hash",
    "manifest_hash",
    "sample_size",
    "denominators",
    "dominant_transitions",
    "limitations",
    "analyst_rationale",
    "alternative_explanations",
    "development_exposed",
    "holdout_required",
    "analyst_id",
)


def build_decision_record(
    *,
    manifest: AnalysisManifest,
    rows: list[SnapshotItemRecord],
    outcome: str,
    analyst_id: str,
    analyst_rationale: str,
    alternative_explanations: list[str] | None = None,
    limitations: list[str] | None = None,
    relevant_strata: list[str] | None = None,
    holdout_plan: HoldoutPlan | None = None,
) -> DecisionGateRecord:
    if outcome not in DECISION_OUTCOMES:
        raise ValueError(f"Invalid decision outcome: {outcome!r}")

    dash = descriptive_dashboard(rows)
    holdout_required = outcome == "F_candidate_ruleset_hypothesis_justified"
    if holdout_required and holdout_plan is None:
        raise ValueError(
            "Outcome F requires a holdout plan before authorizing a future proposal phase."
        )
    if holdout_required and holdout_plan is not None and holdout_plan.overlap_errors:
        raise ValueError(
            "Outcome F holdout plan has overlap errors; fix separation before recording."
        )

    exposed = any(r.contamination_status == "development_exposed" for r in rows)
    second_avail = any(bool(r.second_review_id) for r in rows)

    return DecisionGateRecord(
        analysis_id=manifest.analysis_id,
        outcome=outcome,
        snapshot_hash=manifest.snapshot_hash,
        manifest_hash=manifest.manifest_hash,
        sample_size=int(dash["selected_unique_items"]),
        denominators={
            "selected_unique_items": int(dash["selected_unique_items"]),
            "eligible_comparable_items": int(dash["eligible_comparable_items"]),
            "exact_label_matches": int(dash["exact_label_matches"]),
            "morphology_disagreements": int(dash["morphology_disagreements"]),
            "expert_abstentions": int(dash["expert_abstentions"]),
            "candidate_abstentions": int(dash["candidate_abstentions"]),
            "both_abstained": int(dash["both_abstained"]),
            "non_comparable_items": int(dash["non_comparable_items"]),
            "unavailable_items": int(dash["unavailable_items"]),
        },
        dominant_transitions=dominant_transitions(rows),
        relevant_strata=list(relevant_strata or []),
        limitations=list(
            limitations
            or [
                "Descriptive analysis only; neither expert nor candidate is ground truth.",
                "Pilot sample may be development-exposed.",
            ]
        ),
        independent_second_review_available=second_avail,
        analyst_rationale=analyst_rationale,
        alternative_explanations=list(alternative_explanations or []),
        development_exposed=exposed or manifest.contamination_status == "development_exposed",
        holdout_required=holdout_required,
        holdout_plan_id=holdout_plan.holdout_plan_id if holdout_plan else "",
        analyst_id=analyst_id,
    )


def validate_decision_record(record: DecisionGateRecord) -> list[str]:
    issues: list[str] = []
    data = record.to_dict()
    for key in REQUIRED_DECISION_FIELDS:
        if data.get(key) in (None, "", [], {}):
            if key == "alternative_explanations" and data.get(key) == []:
                issues.append("missing_alternative_explanations")
            elif key != "alternative_explanations":
                issues.append(f"missing_{key}")
    if record.outcome not in DECISION_OUTCOMES:
        issues.append("invalid_outcome")
    if record.outcome == "F_candidate_ruleset_hypothesis_justified":
        if not record.holdout_required:
            issues.append("outcome_f_must_require_holdout")
        if not record.holdout_plan_id:
            issues.append("outcome_f_missing_holdout_plan_id")
    if not record.analyst_rationale.strip():
        issues.append("empty_rationale")
    return issues


def outcome_labels(lang: str = "en") -> dict[str, str]:
    if lang == "ru":
        return {
            "A_insufficient_evidence": "A. Недостаточно данных — собрать больше экспертных оценок",
            "B_no_candidate_change": "B. Изменение кандидата не обосновано",
            "C_documentation_or_label_clarification": (
                "C. Нужно уточнение документации или определения меток"
            ),
            "D_data_assessability_interference_investigation": (
                "D. Нужно исследование данных / оценимости / помех"
            ),
            "E_upstream_geometry_evidence_investigation": (
                "E. Нужно исследование upstream геометрии / evidence"
            ),
            "F_candidate_ruleset_hypothesis_justified": (
                "F. Гипотеза о правилах кандидата обоснована для отдельной будущей фазы"
            ),
        }
    return {
        "A_insufficient_evidence": "A. Insufficient evidence — collect more expert reviews",
        "B_no_candidate_change": "B. No candidate change justified",
        "C_documentation_or_label_clarification": (
            "C. Documentation or label-definition clarification needed"
        ),
        "D_data_assessability_interference_investigation": (
            "D. Data/assessability/interference investigation needed"
        ),
        "E_upstream_geometry_evidence_investigation": (
            "E. Upstream geometry/evidence investigation needed"
        ),
        "F_candidate_ruleset_hypothesis_justified": (
            "F. Candidate ruleset hypothesis justified for a separate future phase"
        ),
    }
