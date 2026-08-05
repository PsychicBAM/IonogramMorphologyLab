"""Dataset contamination tracking for development-exposed analysis items."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    ContaminationRecord,
    SnapshotItemRecord,
)


def mark_development_exposed(
    rows: list[SnapshotItemRecord],
    *,
    analysis_id: str,
) -> list[ContaminationRecord]:
    records: list[ContaminationRecord] = []
    for r in rows:
        if not r.comparison_id and r.eligibility_bucket != "eligible_comparable":
            # Still mark items inspected in frozen analysis when they have identities
            if not r.item_id:
                continue
        source_date = (r.frame_time or "")[:10]
        rec = ContaminationRecord(
            analysis_id=analysis_id,
            cohort_id=r.cohort_id,
            item_id=r.item_id,
            source_sha256=r.source_sha256,
            source_date=source_date,
            related_frame_group=r.related_frame_group,
            sequence_id=r.sequence_id,
            status="development_exposed",
        )
        r.contamination_status = "development_exposed"
        records.append(rec)
    return records


def exposed_identity_index(records: list[ContaminationRecord]) -> dict[str, Any]:
    item_keys = {f"{r.cohort_id}:{r.item_id}" for r in records}
    shas = {r.source_sha256 for r in records if r.source_sha256}
    dates = {r.source_date for r in records if r.source_date}
    groups = {r.related_frame_group for r in records if r.related_frame_group}
    seqs = {r.sequence_id for r in records if r.sequence_id}
    return {
        "item_keys": sorted(item_keys),
        "source_shas": sorted(shas),
        "source_dates": sorted(dates),
        "related_frame_groups": sorted(groups),
        "sequence_ids": sorted(seqs),
    }


def reject_untouched_holdout(
    proposed_holdout_keys: list[str],
    contamination_records: list[ContaminationRecord],
) -> dict[str, Any]:
    """Reject designating development-exposed items as untouched holdout."""
    exposed = exposed_identity_index(contamination_records)
    exposed_items = set(exposed["item_keys"])
    proposed = set(proposed_holdout_keys)
    overlap_items = sorted(proposed.intersection(exposed_items))
    # also check related groups / sequences if keys encode them as cohort:item
    warnings: list[str] = []
    errors: list[str] = []
    if overlap_items:
        errors.append(
            "Exposed items cannot be designated as an untouched independent holdout."
        )
    return {
        "allowed": not errors,
        "overlap_item_keys": overlap_items,
        "errors": errors,
        "warnings": warnings,
        "message_en": (
            "One or more proposed holdout items were previously frozen into a "
            "disagreement analysis (development-exposed)."
            if overlap_items
            else ""
        ),
        "message_ru": (
            "Один или несколько предложенных элементов holdout ранее были "
            "заморожены в анализе расхождений (development-exposed)."
            if overlap_items
            else ""
        ),
    }
