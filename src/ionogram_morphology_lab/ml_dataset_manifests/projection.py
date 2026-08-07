"""Project readiness inventory into candidate-independent manifest items."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.ml_dataset_manifests.models import ManifestItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    is_time_only_value,
    is_valid_acquisition_date,
    normalize_acquisition_date,
    resolve_acquisition_date,
)
from ionogram_morphology_lab.ml_dataset_readiness.contracts import REQUIRED_FIELDS_BY_CONTRACT
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord


def _target_label(row: InventoryItemRecord, task_contract: str) -> str:
    if task_contract == "spread_f_morphology_classification":
        return row.morphology or ""
    if task_contract == "assessability_quality_classification":
        parts = [row.assessability or "", row.ambiguity or ""]
        return "|".join(p for p in parts if p)
    if task_contract == "interference_classification":
        return ",".join(sorted(row.interference or []))
    if task_contract == "ionogram_parameter_scaling":
        return ""  # never infer from morphology
    return ""


def normalized_acquisition_date_from_inventory(row: InventoryItemRecord) -> str:
    """Reuse ML-A.1a.1 acquisition-date authority. Never use frame_time."""
    existing = str(row.source_date or "").strip()
    if is_valid_acquisition_date(existing):
        return normalize_acquisition_date(existing)
    # Legacy / inconsistent readiness rows may store HH:MM in source_date.
    # Drop time-only values and re-resolve via shared authority (filename, etc.).
    grouping: dict[str, Any] = {}
    if existing and not is_time_only_value(existing):
        grouping["source_date"] = existing
    # Never pass frame_time / review timestamps into the resolver.
    return resolve_acquisition_date(
        source_inventory_date="",
        cohort_manifest_date="",
        grouping=grouping,
        datetime_metadata="",
        source_display_name=str(row.source_display_name or ""),
        mat_metadata_date="",
    )


def project_manifest_items(
    inventory: list[InventoryItemRecord],
    *,
    task_contract: str,
    project_id: str = "",
) -> tuple[list[ManifestItemRecord], dict[str, Any]]:
    """One current item per (project, cohort, revision, item, task_contract)."""
    accounting: dict[str, Any] = {
        "raw_inventory_rows": len(inventory),
        "unique_current_items": 0,
        "deduplicated": 0,
        "excluded": 0,
        "exclusion_reasons": {},
        "fail_closed": [],
        "candidate_fields_consulted": False,
        "acquisition_dates_normalized": 0,
        "time_only_source_date_rejected": 0,
    }
    seen: dict[str, ManifestItemRecord] = {}
    for row in inventory:
        # Fail closed on missing source SHA
        if not row.source_sha256:
            accounting["fail_closed"].append(
                f"missing_source_sha:{row.cohort_id}:{row.item_id}"
            )
            accounting["excluded"] += 1
            accounting["exclusion_reasons"]["missing_source_sha"] = (
                accounting["exclusion_reasons"].get("missing_source_sha", 0) + 1
            )
            continue
        if row.cohort_revision is None or int(row.cohort_revision) < 0:
            accounting["fail_closed"].append(
                f"unresolved_cohort_revision:{row.cohort_id}:{row.item_id}"
            )
            accounting["excluded"] += 1
            accounting["exclusion_reasons"]["unresolved_cohort_revision"] = (
                accounting["exclusion_reasons"].get("unresolved_cohort_revision", 0) + 1
            )
            continue

        pid = project_id or row.project_id or ""
        target = _target_label(row, task_contract)
        required = REQUIRED_FIELDS_BY_CONTRACT.get(task_contract, ())
        invalid_label = False
        if task_contract == "spread_f_morphology_classification" and not target:
            invalid_label = True
        if task_contract == "ionogram_parameter_scaling":
            invalid_label = True  # unsupported unless genuine labels exist (ML-A marks)

        exclusion = row.exclusion_reason or ""
        role_default = "excluded"
        if row.contamination_state == "prohibited_invalid" or row.identity_issues:
            exclusion = exclusion or "prohibited_invalid_or_identity_issues"
        elif invalid_label and task_contract == "ionogram_parameter_scaling":
            exclusion = exclusion or "parameter_scaling_unsupported"
        elif invalid_label:
            exclusion = exclusion or "invalid_task_label"
            accounting["fail_closed"].append(
                f"invalid_task_label:{row.cohort_id}:{row.item_id}"
            )
        else:
            role_default = "excluded"  # assigned later by planning

        if is_time_only_value(str(row.source_date or "")):
            accounting["time_only_source_date_rejected"] += 1
        source_date = normalized_acquisition_date_from_inventory(row)
        if source_date and source_date != str(row.source_date or "").strip():
            accounting["acquisition_dates_normalized"] += 1

        # Preserve frame_time separately; never use it as acquisition date.
        frame_time = str(row.frame_time or "")
        if is_valid_acquisition_date(frame_time) and frame_time == source_date:
            # Unusual; leave as-is. Do not copy date into frame_time.
            pass

        item = ManifestItemRecord(
            project_id=pid,
            cohort_id=row.cohort_id,
            cohort_revision=int(row.cohort_revision),
            item_id=row.item_id,
            task_contract=task_contract,
            source_inventory_id=row.source_inventory_id,
            source_display_name=row.source_display_name,
            source_sha256=row.source_sha256,
            source_date=source_date,
            frame_index=int(row.frame_index),
            frame_time=frame_time,
            related_frame_group=row.related_frame_group,
            sequence_id=row.sequence_id,
            campaign_id=row.campaign_id or "",
            acquisition_period=source_date or "",
            morphology=row.morphology,
            assessability=row.assessability,
            ambiguity=row.ambiguity,
            interference=list(row.interference or []),
            reviewer_role=row.reviewer_role,
            reviewer_alias=row.reviewer_alias,
            contamination_state=row.contamination_state,
            eligible_future_development=bool(row.eligible_future_development),
            eligible_untouched_holdout=bool(row.eligible_untouched_holdout),
            exclusion_reason=exclusion,
            missingness_category=row.missingness_category,
            independent_second_review_available=bool(
                row.independent_second_review_available
            ),
            target_label=target,
            role=role_default,
            identity_issues=list(row.identity_issues or []),
        )
        key = item.identity_key()
        if key in seen:
            accounting["deduplicated"] += 1
            continue
        # Corrected review history already resolved in readiness inventory as current
        seen[key] = item

    out = [seen[k] for k in sorted(seen.keys())]
    accounting["unique_current_items"] = len(out)
    accounting["required_fields"] = list(required)
    accounting["unique_acquisition_dates"] = sorted(
        {it.source_date for it in out if is_valid_acquisition_date(it.source_date)}
    )
    return out, accounting
