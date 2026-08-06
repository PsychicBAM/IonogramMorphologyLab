"""Missingness accounting with separated categories."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.constants import MISSINGNESS_CATEGORIES
from ionogram_morphology_lab.ml_dataset_readiness.contracts import REQUIRED_FIELDS_BY_CONTRACT
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord


def build_missingness_report(
    rows: list[InventoryItemRecord],
    *,
    task_contract: str,
) -> dict[str, Any]:
    by_cat: Counter[str] = Counter()
    field_gaps: Counter[str] = Counter()
    required = REQUIRED_FIELDS_BY_CONTRACT.get(task_contract, ())

    for r in rows:
        cat = r.missingness_category or ""
        if cat:
            if cat not in MISSINGNESS_CATEGORIES:
                cat = "structurally_missing"
            by_cat[cat] += 1
        if "expert_morphology" in required and not r.morphology:
            field_gaps["missing_morphology"] += 1
        if "assessability" in required and not r.assessability:
            field_gaps["missing_assessability"] += 1
        if "interference" in required and not r.interference:
            field_gaps["missing_interference_state"] += 1
        if not r.source_sha256:
            field_gaps["missing_source_sha"] += 1
        if not r.source_date:
            field_gaps["missing_source_date"] += 1
        if not r.frame_time:
            field_gaps["missing_frame_time"] += 1
        if not r.related_frame_group:
            field_gaps["missing_related_frame_group"] += 1
        if not r.reviewer_alias:
            field_gaps["missing_reviewer_identity"] += 1
        if not r.locked_first_review_id:
            field_gaps["unlocked_or_draft_review"] += 1
        if r.first_review_corrected and not r.locked_first_review_id:
            field_gaps["unresolved_correction_chain"] += 1
        if "ambiguity" in required and not r.ambiguity:
            field_gaps["missing_ambiguity"] += 1

    # Ensure all categories appear explicitly (zero-filled)
    categories = {c: int(by_cat.get(c, 0)) for c in sorted(MISSINGNESS_CATEGORIES)}
    complete = sum(1 for r in rows if not r.missingness_category)

    return {
        "task_contract": task_contract,
        "categories": categories,
        "complete_rows": complete,
        "field_gaps": dict(field_gaps),
        "note_en": (
            "Categories are kept separate: structurally missing, not applicable, "
            "expert abstained, unavailable data, corrupted identity."
        ),
    }
