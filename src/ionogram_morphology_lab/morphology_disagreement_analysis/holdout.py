"""Holdout planning — untouched groups only; no modified-ruleset evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_disagreement_analysis.contamination import (
    exposed_identity_index,
    reject_untouched_holdout,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    ContaminationRecord,
    HoldoutPlan,
    SnapshotItemRecord,
)


def _case_key(r: SnapshotItemRecord) -> str:
    return f"{r.cohort_id}:{r.item_id}"


def detect_overlap(
    development: list[SnapshotItemRecord],
    holdout: list[SnapshotItemRecord],
    *,
    holdout_external_keys: list[str] | None = None,
    contamination_records: list[ContaminationRecord] | None = None,
) -> dict[str, Any]:
    dev_items = {_case_key(r) for r in development}
    hold_items = {_case_key(r) for r in holdout}
    if holdout_external_keys:
        hold_items |= set(holdout_external_keys)
    item_overlap = sorted(dev_items.intersection(hold_items))

    dev_groups = {r.related_frame_group for r in development if r.related_frame_group}
    hold_groups = {r.related_frame_group for r in holdout if r.related_frame_group}
    group_overlap = sorted(dev_groups.intersection(hold_groups))

    dev_seq = {r.sequence_id for r in development if r.sequence_id}
    hold_seq = {r.sequence_id for r in holdout if r.sequence_id}
    seq_overlap = sorted(dev_seq.intersection(hold_seq))

    dev_dates = {(r.source_sha256, (r.frame_time or "")[:10]) for r in development}
    hold_dates = {(r.source_sha256, (r.frame_time or "")[:10]) for r in holdout}
    date_overlap = sorted(
        f"{a}:{b}" for a, b in dev_dates.intersection(hold_dates) if a or b
    )

    errors: list[str] = []
    warnings: list[str] = []
    if item_overlap:
        errors.append("overlapping_item_identity")
    if group_overlap:
        errors.append("overlapping_related_frame_group")
    if seq_overlap:
        errors.append("overlapping_sequence")
    if date_overlap:
        warnings.append("overlapping_source_date")

    if contamination_records:
        exposed = exposed_identity_index(contamination_records)
        # External holdout keys must not collide with exposed related groups/sequences
        # when those metadata are encoded in contamination records.
        for key in holdout_external_keys or []:
            # key format cohort:item — item-level exposure checked separately
            if key in exposed["item_keys"]:
                if "overlapping_item_identity" not in errors:
                    errors.append("overlapping_item_identity")

    return {
        "ok": not errors,
        "item_overlap": item_overlap,
        "related_frame_group_overlap": group_overlap,
        "sequence_overlap": seq_overlap,
        "source_date_overlap": date_overlap,
        "errors": errors,
        "warnings": warnings,
    }


def build_holdout_plan(
    *,
    analysis_id: str,
    title: str,
    all_rows: list[SnapshotItemRecord],
    holdout_case_keys: list[str],
    contamination_records: list[ContaminationRecord],
    separation_basis: list[str] | None = None,
) -> HoldoutPlan:
    """Build a holdout plan.

    Holdout keys should prefer untouched external identities (not already frozen
    into this analysis). Keys that appear in ``all_rows`` are treated as an
    in-sample split and checked for related-frame/sequence overlap.
    """
    key_set = set(holdout_case_keys)
    in_sample = [r for r in all_rows if _case_key(r) in key_set]
    development_rows = [r for r in all_rows if _case_key(r) not in key_set]
    external_keys = sorted(key_set - {_case_key(r) for r in all_rows})

    contam = reject_untouched_holdout(holdout_case_keys, contamination_records)
    overlap = detect_overlap(
        development_rows if in_sample else all_rows,
        in_sample,
        holdout_external_keys=external_keys,
        contamination_records=contamination_records,
    )

    errors = list(overlap["errors"])
    warnings = list(overlap["warnings"])
    if not contam["allowed"]:
        errors.extend(contam["errors"])
        warnings.append("development_exposed_holdout_rejected")

    if not holdout_case_keys:
        errors.append("holdout_empty")

    plan = HoldoutPlan(
        holdout_plan_id=f"holdout_{uuid4().hex[:12]}",
        analysis_id=analysis_id,
        title=title,
        created_at=datetime.now(timezone.utc).isoformat(),
        development_case_keys=sorted(_case_key(r) for r in all_rows),
        holdout_case_keys=sorted(holdout_case_keys),
        separation_basis=list(
            separation_basis
            or ["source_date", "sequence", "related_frame_group", "campaign"]
        ),
        overlap_warnings=warnings,
        overlap_errors=errors,
        candidate_reveal_blocked=True,
    )
    plan.plan_hash = plan.compute_hash()
    return plan


def validate_holdout_plan(plan: HoldoutPlan) -> list[str]:
    issues: list[str] = []
    if plan.overlap_errors:
        issues.extend(f"holdout_error:{e}" for e in plan.overlap_errors)
    if not plan.holdout_case_keys:
        issues.append("holdout_empty")
    if not plan.candidate_reveal_blocked:
        issues.append("holdout_must_block_candidate_reveal")
    expected = plan.compute_hash()
    if plan.plan_hash and plan.plan_hash != expected:
        issues.append("holdout_plan_hash_mismatch")
    return issues
