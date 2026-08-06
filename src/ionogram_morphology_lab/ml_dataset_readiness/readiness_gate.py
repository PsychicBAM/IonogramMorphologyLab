"""Formal Readiness Gate — ML-B planning authorization only for outcome F."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.constants import GATE_OUTCOMES
from ionogram_morphology_lab.ml_dataset_readiness.models import (
    HoldoutFeasibilityReport,
    ReadinessGateRecord,
    ReadinessManifest,
)


GATE_LABELS: dict[str, dict[str, str]] = {
    "A_collect_more_expert_labels": {
        "en": "A. Not ready — collect more expert labels",
        "ru": "A. Не готово — собрать больше экспертных меток",
    },
    "B_repair_label_contract_or_missing_data": {
        "en": "B. Not ready — repair label contract or missing data",
        "ru": "B. Не готово — исправить контракт меток или недостающие данные",
    },
    "C_expand_class_source_date_sequence_coverage": {
        "en": "C. Not ready — expand class/source/date/sequence coverage",
        "ru": "C. Не готово — расширить покрытие классов/источников/дат/последовательностей",
    },
    "D_obtain_independent_expert_review": {
        "en": "D. Not ready — obtain independent expert review",
        "ru": "D. Не готово — получить независимую экспертную оценку",
    },
    "E_untouched_holdout_not_currently_feasible": {
        "en": "E. Not ready — untouched holdout is not currently feasible",
        "ru": "E. Не готово — нетронутый holdout сейчас невозможен",
    },
    "F_ready_for_mlb_manifest_planning_only": {
        "en": "F. Ready to proceed to ML-B manifest planning only",
        "ru": "F. Готово только к планированию манифестов ML-B",
    },
}

REQUIRED_GATE_FIELDS = (
    "outcome",
    "task_contract",
    "audit_snapshot_hash",
    "manifest_hash",
    "unique_item_count",
    "unique_related_frame_groups",
    "unique_sequences",
    "unique_dates",
    "class_distribution",
    "missingness",
    "reviewer_independence",
    "contamination",
    "holdout_feasibility",
    "limitations",
    "required_next_actions",
    "analyst_id",
)


def outcome_labels(lang: str = "en") -> list[tuple[str, str]]:
    return [(k, GATE_LABELS[k].get(lang) or GATE_LABELS[k]["en"]) for k in sorted(GATE_OUTCOMES)]


def build_gate_record(
    *,
    manifest: ReadinessManifest,
    coverage: dict[str, Any],
    missingness: dict[str, Any],
    feasibility: HoldoutFeasibilityReport,
    outcome: str,
    blockers: list[str] | None,
    analyst_id: str,
    analyst_rationale: str,
    required_next_actions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> ReadinessGateRecord:
    if outcome not in GATE_OUTCOMES:
        raise ValueError(f"Invalid gate outcome: {outcome!r}")
    if outcome == "F_ready_for_mlb_manifest_planning_only":
        # Do not auto-select F solely because integrity passed — require explicit rationale
        if not str(analyst_rationale or "").strip():
            raise ValueError(
                "Outcome F requires an explicit analyst rationale; "
                "integrity validation alone does not authorize F."
            )
        if not feasibility.class_aware_group_separated_holdout_appears_possible:
            raise ValueError(
                "Outcome F rejected: holdout feasibility assessment does not "
                "indicate a class-aware group-separated holdout appears possible."
            )

    dens = coverage.get("denominators") or {}
    contam = {
        "development_exposed_items": dens.get("development_exposed_items", 0),
        "untouched_eligible_items": dens.get("untouched_eligible_items", 0),
    }
    return ReadinessGateRecord(
        audit_id=manifest.audit_id,
        outcome=outcome,
        blockers=list(blockers or []),
        task_contract=manifest.task_contract,
        audit_snapshot_hash=manifest.inventory_hash,
        manifest_hash=manifest.manifest_hash,
        unique_item_count=int(dens.get("unique_current_items", 0)),
        unique_related_frame_groups=int(dens.get("unique_related_frame_groups", 0)),
        unique_sequences=int(dens.get("unique_sequences", 0)),
        unique_dates=int(dens.get("unique_source_dates", 0)),
        class_distribution=dict(coverage.get("morphology_label_counts") or {}),
        missingness=dict((missingness or {}).get("categories") or {}),
        reviewer_independence=dict(coverage.get("reviewer_independence") or {}),
        contamination=contam,
        holdout_feasibility={
            "assessment_kind": feasibility.assessment_kind,
            "appears_possible": feasibility.class_aware_group_separated_holdout_appears_possible,
            "untouched_eligible_groups": list(feasibility.untouched_eligible_groups),
            "classes_absent_from_untouched": list(feasibility.classes_absent_from_untouched),
        },
        limitations=list(
            limitations
            or [
                "Descriptive readiness audit only; expert labels are not ground truth.",
                "No model training, architecture selection, or production integration authorized.",
                "Outcome F authorizes ML-B manifest planning only.",
            ]
        ),
        required_next_actions=list(required_next_actions or []),
        analyst_id=analyst_id,
        analyst_rationale=analyst_rationale,
    )


def validate_gate_record(record: ReadinessGateRecord) -> list[str]:
    errors: list[str] = []
    data = record.to_dict()
    for f in REQUIRED_GATE_FIELDS:
        if f not in data or data[f] in (None, ""):
            if f in ("blockers", "limitations", "required_next_actions"):
                continue
            if isinstance(data.get(f), (dict, list)) and data.get(f) is not None:
                continue
            errors.append(f"missing_field:{f}")
    if record.authorizes_training:
        errors.append("policy_violation:authorizes_training")
    if record.authorizes_architecture_selection:
        errors.append("policy_violation:authorizes_architecture_selection")
    if record.authorizes_holdout_evaluation:
        errors.append("policy_violation:authorizes_holdout_evaluation")
    if record.authorizes_production_integration:
        errors.append("policy_violation:authorizes_production_integration")
    if record.outcome == "F_ready_for_mlb_manifest_planning_only":
        if not record.authorizes_mlb_manifest_planning_only:
            errors.append("outcome_f_must_flag_mlb_planning_only")
    return errors


def suggest_gate_blockers(
    *,
    coverage: dict[str, Any],
    missingness: dict[str, Any],
    feasibility: HoldoutFeasibilityReport | None = None,
    task_contract: str = "",
) -> list[dict[str, str]]:
    """Return auto-suggested blockers with evidence.

    Manual selection remains allowed for any blocker. Blocker B is suggested
    only when there is actual label-contract / missing-data evidence.
    """
    suggestions: list[dict[str, str]] = []
    dens = coverage.get("denominators") or {}
    cats = (missingness or {}).get("categories") or {}
    missing_required = int(cats.get("structurally_missing") or dens.get("missing_required_fields") or 0)
    unavailable = int(cats.get("unavailable_data") or dens.get("unavailable_sources") or 0)
    corrupted = int(cats.get("corrupted_identity") or 0)
    unsupported = bool(coverage.get("target_unsupported"))
    contract_note = ""
    if task_contract == "ionogram_parameter_scaling" and unsupported:
        contract_note = "parameter_scaling_unsupported"

    # B — only with concrete evidence
    if missing_required > 0 or unavailable > 0 or corrupted > 0 or contract_note:
        evidence_parts = []
        if missing_required:
            evidence_parts.append(f"missing_required_fields={missing_required}")
        if unavailable:
            evidence_parts.append(f"unavailable_sources={unavailable}")
        if corrupted:
            evidence_parts.append(f"corrupted_identity={corrupted}")
        if contract_note:
            evidence_parts.append(contract_note)
        suggestions.append(
            {
                "code": "B_repair_label_contract_or_missing_data",
                "evidence": "; ".join(evidence_parts),
            }
        )

    locked = int(dens.get("locked_first_reviews") or 0)
    if locked < int(dens.get("unique_current_items") or 0) or locked < 5:
        suggestions.append(
            {
                "code": "A_collect_more_expert_labels",
                "evidence": f"locked_first_reviews={locked}",
            }
        )

    if int(dens.get("unique_source_dates") or 0) <= 1 or int(
        dens.get("unique_sequences") or 0
    ) <= 1:
        suggestions.append(
            {
                "code": "C_expand_class_source_date_sequence_coverage",
                "evidence": (
                    f"unique_source_dates={dens.get('unique_source_dates')}; "
                    f"unique_sequences={dens.get('unique_sequences')}"
                ),
            }
        )

    if int(dens.get("independent_second_reviews") or 0) == 0:
        suggestions.append(
            {
                "code": "D_obtain_independent_expert_review",
                "evidence": "independent_second_reviews=0",
            }
        )

    if feasibility is not None and not (
        feasibility.class_aware_group_separated_holdout_appears_possible
    ):
        suggestions.append(
            {
                "code": "E_untouched_holdout_not_currently_feasible",
                "evidence": (
                    f"untouched_groups={len(feasibility.untouched_eligible_groups)}; "
                    f"exposed_groups={len(feasibility.development_exposed_groups)}"
                ),
            }
        )
    return suggestions
