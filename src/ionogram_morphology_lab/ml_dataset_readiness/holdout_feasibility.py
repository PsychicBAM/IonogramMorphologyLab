"""Holdout feasibility assessment only — never creates final ML-B manifests."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.models import (
    HoldoutFeasibilityReport,
    InventoryItemRecord,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES


def assess_holdout_feasibility(
    rows: list[InventoryItemRecord],
    *,
    audit_id: str,
) -> HoldoutFeasibilityReport:
    """Simulate group-separated holdout feasibility without splitting groups/sequences."""
    # Group unit = related_frame_group (fallback sequence, then source_date+sha)
    group_members: dict[str, list[InventoryItemRecord]] = defaultdict(list)
    for r in rows:
        gk = r.related_frame_group or r.sequence_id or f"{r.source_sha256}:{r.source_date}"
        group_members[gk].append(r)

    untouched_groups: list[str] = []
    exposed_groups: list[str] = []
    overlapping: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    for gk, members in group_members.items():
        states = {m.contamination_state for m in members}
        elig = all(m.eligible_untouched_holdout for m in members)
        any_exposed = any(m.contamination_state == "development_exposed" for m in members)
        if any_exposed and elig:
            overlapping.append(gk)
            errors.append(f"group_mixed_exposure:{gk}")
        if any_exposed:
            exposed_groups.append(gk)
            # propagate: entire group unsuitable
            for m in members:
                if m.contamination_state != "development_exposed":
                    warnings.append(
                        f"exposure_propagation:{gk}:{m.item_id}"
                    )
        elif elig and "prohibited_invalid" not in states:
            untouched_groups.append(gk)
        else:
            exposed_groups.append(gk)

    # Never allow random frame-level split markers
    warnings.append(
        "Random frame-level splitting is prohibited; grouping units are "
        "source/date/sequence/related-frame-group/campaign."
    )

    classes_untouched: Counter[str] = Counter()
    for gk in untouched_groups:
        for m in group_members[gk]:
            if m.morphology:
                classes_untouched[m.morphology] += 1

    absent = sorted(HUMAN_MORPHOLOGY_CODES - set(classes_untouched.keys()))

    dates_exposed = {
        m.source_date
        for gk in exposed_groups
        for m in group_members[gk]
        if m.source_date
    }
    dates_untouched = {
        m.source_date
        for gk in untouched_groups
        for m in group_members[gk]
        if m.source_date
    }
    dates_only_exposed = sorted(dates_exposed - dates_untouched)

    sources_exposed = {
        m.source_sha256
        for gk in exposed_groups
        for m in group_members[gk]
        if m.source_sha256
    }
    sources_untouched = {
        m.source_sha256
        for gk in untouched_groups
        for m in group_members[gk]
        if m.source_sha256
    }
    sources_only_exposed = sorted(sources_exposed - sources_untouched)

    # Feasible only if at least two untouched groups and at least two classes present
    appears_possible = (
        len(untouched_groups) >= 2
        and len(classes_untouched) >= 2
        and not overlapping
        and len(absent) < len(HUMAN_MORPHOLOGY_CODES)
    )
    if not appears_possible:
        warnings.append(
            "Class-aware group-separated holdout does not currently appear feasible."
        )

    # Detect attempted sequence splits would be an error if same sequence in both
    seq_to_sides: dict[str, set[str]] = defaultdict(set)
    for gk in untouched_groups:
        for m in group_members[gk]:
            if m.sequence_id:
                seq_to_sides[m.sequence_id].add("untouched")
    for gk in exposed_groups:
        for m in group_members[gk]:
            if m.sequence_id:
                seq_to_sides[m.sequence_id].add("exposed")
    for seq, sides in seq_to_sides.items():
        if sides == {"untouched", "exposed"}:
            # sequence spans both — must not split; treat as exposed for feasibility
            errors.append(f"sequence_cannot_be_split:{seq}")
            overlapping.append(seq)

    return HoldoutFeasibilityReport(
        audit_id=audit_id,
        untouched_eligible_groups=sorted(set(untouched_groups)),
        development_exposed_groups=sorted(set(exposed_groups)),
        overlapping_groups=sorted(set(overlapping)),
        classes_in_untouched=dict(classes_untouched),
        classes_absent_from_untouched=absent,
        dates_only_in_exposed=dates_only_exposed,
        sources_only_in_exposed=sources_only_exposed,
        class_aware_group_separated_holdout_appears_possible=appears_possible
        and not any(e.startswith("sequence_cannot_be_split") for e in errors),
        warnings=warnings,
        errors=errors,
    )


def collection_gap_plan(
    rows: list[InventoryItemRecord],
    feasibility: HoldoutFeasibilityReport,
    coverage: dict[str, Any],
) -> list[str]:
    """Descriptive data-collection gap plan (grouping units, not universal N)."""
    actions: list[str] = []
    dens = coverage.get("denominators") or {}
    morph = coverage.get("morphology_label_counts") or {}
    absent = coverage.get("absent_morphology_classes") or []

    if dens.get("unique_source_dates", 0) <= 1:
        actions.append(
            "Collect expert labels from at least several additional independent "
            "source dates and sequences."
        )
    if dens.get("independent_second_reviews", 0) == 0:
        actions.append(
            "Obtain independent second expert reviews (same expert corrections "
            "do not count)."
        )
    if "range_spread" in absent:
        actions.append("Range-spread class is absent — collect labelled examples.")
    if "mixed_spread" in morph and morph.get("mixed_spread", 0) == dens.get(
        "unique_current_items", 0
    ):
        actions.append(
            "Strong concentration in mixed-spread — expand morphology class coverage."
        )
    if dens.get("partially_assessable", 0) > dens.get("assessable", 0):
        actions.append(
            "Too many partially assessable frames relative to assessable — "
            "improve assessability coverage."
        )
    interf = coverage.get("interference_counts") or {}
    if interf.get("vertical_interference", 0) > (
        dens.get("unique_current_items", 1) // 2
    ):
        actions.append(
            "Vertical interference dominates — collect cleaner sequences where possible."
        )
    if dens.get("development_exposed_items", 0) >= dens.get("unique_current_items", 0):
        actions.append(
            "All available examples are development-exposed — collect new untouched "
            "source dates/sequences for holdout feasibility."
        )
    if feasibility.classes_absent_from_untouched:
        actions.append(
            "Untouched groups lack required classes: "
            + ", ".join(feasibility.classes_absent_from_untouched)
        )
    if not feasibility.class_aware_group_separated_holdout_appears_possible:
        actions.append(
            "Untouched holdout is not currently feasible — expand independent "
            "grouping units before ML-B."
        )
    if not actions:
        actions.append(
            "Coverage appears structurally broader; still confirm Readiness Gate "
            "before ML-B manifest planning."
        )
    return actions
