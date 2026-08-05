"""Resolve eligible / excluded items for disagreement analysis."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ionogram_morphology_lab.morphology_disagreement_analysis.models import SnapshotItemRecord
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    project_cohort_comparisons,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import map_candidate_state_to_human
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _grouping(item) -> dict[str, str]:
    g = getattr(item, "grouping", None) or {}
    if isinstance(g, dict):
        return {str(k): str(v) for k, v in g.items()}
    return {}


def _evidence_categories(snap) -> list[str]:
    if snap is None:
        return []
    ledger = getattr(snap, "evidence_ledger", None) or []
    cats: list[str] = []
    for row in ledger:
        if not isinstance(row, dict):
            continue
        cat = str(row.get("category") or row.get("evidence_type") or "").strip()
        if cat and cat not in cats:
            cats.append(cat)
    return cats


def resolve_cohort_items(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    campaign_id: str = "",
    require_revealed: bool = True,
) -> tuple[list[SnapshotItemRecord], dict[str, int], list[str]]:
    """Build per-item snapshot rows from current-state projection only."""
    warnings: list[str] = []
    rows: list[SnapshotItemRecord] = []
    buckets: Counter[str] = Counter()

    try:
        manifest = store.load_manifest(cohort_id)
    except Exception as exc:  # noqa: BLE001 — fail closed into exclusion accounting
        warnings.append(f"cohort_unreadable:{cohort_id}:{exc}")
        buckets["invalid_identity"] += 1
        return rows, dict(buckets), warnings

    if require_revealed and not bool(getattr(manifest, "frozen", False)):
        warnings.append(f"cohort_not_frozen:{cohort_id}")
        buckets["blind_not_revealed"] += 1
        return rows, dict(buckets), warnings

    items = {it.item_id: it for it in store.load_items(cohort_id)}
    snaps = {}
    for it in items.values():
        snap = store.candidate_snapshot_for_item(cohort_id, it.item_id)
        if snap is not None:
            snaps[it.item_id] = snap

    # Blind gate: comparisons must exist; incomplete blind rounds are rejected.
    if require_revealed:
        proj_probe = project_cohort_comparisons(store, cohort_id)
        if proj_probe.current_count == 0:
            locked = 0
            for iid in items:
                if store.locked_review_for_item(cohort_id, iid, review_round=1):
                    locked += 1
            if locked < len(items) or locked == 0:
                warnings.append(f"blind_incomplete:{cohort_id}")
                buckets["blind_not_revealed"] += len(items) or 1
                return rows, dict(buckets), warnings

    proj = project_cohort_comparisons(store, cohort_id)
    cmp_by_item = dict(proj.current_by_item or {})

    for item_id, item in items.items():
        grouping = _grouping(item)
        seq = str(grouping.get("sequence_id") or grouping.get("sequence") or "")
        rel = str(
            grouping.get("related_frame_group")
            or grouping.get("related_group")
            or f"{item.source_sha256}:{item.frame_index}"
        )
        source_date = str(
            grouping.get("source_date")
            or (item.frame_time[:10] if item.frame_time else "")
            or (item.datetime_metadata[:10] if item.datetime_metadata else "")
        )
        r1 = store.locked_review_for_item(cohort_id, item_id, review_round=1)
        r2 = store.locked_review_for_item(cohort_id, item_id, review_round=2)
        snap = snaps.get(item_id)
        cmp_row = cmp_by_item.get(item_id)

        exclusion = ""
        bucket = ""
        available = True

        if str(getattr(item, "item_status", "")) == "item_unavailable":
            bucket = "unavailable_source"
            available = False
        elif r1 is None:
            bucket = "missing_locked_review"
            available = False
        elif snap is None:
            bucket = "unavailable_candidate"
            available = False
        elif cmp_row is None:
            bucket = "missing_current_comparison"
            available = False
        else:
            status = str(cmp_row.get("agreement_status") or "")
            if status == "exact_agreement":
                bucket = "eligible_comparable"
            elif status == "morphology_disagreement":
                bucket = "eligible_comparable"
            elif status == "human_abstained":
                bucket = "expert_abstention"
            elif status == "candidate_abstained":
                bucket = "candidate_abstention"
            elif status == "both_abstained":
                bucket = "both_abstained"
            elif status == "not_comparable":
                bucket = "non_comparable"
            elif status in ("candidate_unavailable",):
                bucket = "unavailable_candidate"
            else:
                # treat assessability_disagreement as comparable descriptive case
                if status == "assessability_disagreement":
                    bucket = "eligible_comparable"
                else:
                    bucket = "non_comparable"
            exclusion = "" if bucket == "eligible_comparable" else bucket

        if not item.source_sha256 or item_id is None:
            bucket = "invalid_identity"
            available = False

        adj_id = ""
        try:
            adjs = store._read_jsonl(store.path_for(cohort_id) / "adjudications.jsonl")
            for adj in adjs:
                if str(adj.get("item_id") or "") == item_id:
                    adj_id = str(adj.get("adjudication_id") or adj.get("id") or "")
        except Exception:
            adj_id = ""

        expert_morph = str(getattr(r1, "morphology", "") or "") if r1 else ""
        cand_state = str(getattr(snap, "candidate_state", "") or "") if snap else ""
        if cmp_row:
            expert_morph = str(cmp_row.get("human_morphology") or expert_morph)
            cand_state = str(cmp_row.get("candidate_state") or cand_state)

        row = SnapshotItemRecord(
            cohort_id=cohort_id,
            item_id=item_id,
            cohort_revision_number=int(getattr(manifest, "revision_number", 1) or 1),
            parent_cohort_id=str(getattr(manifest, "parent_cohort_id", "") or ""),
            campaign_id=campaign_id,
            source_inventory_id=str(item.source_inventory_id or ""),
            source_display_name=str(item.source_display_name or ""),
            source_sha256=str(item.source_sha256 or "").lower(),
            frame_index=int(item.frame_index),
            frame_time=str(item.frame_time or item.datetime_metadata or ""),
            sequence_id=seq,
            related_frame_group=rel,
            expert_review_id=str(getattr(r1, "review_id", "") or "") if r1 else "",
            expert_morphology=expert_morph,
            expert_assessability=str(getattr(r1, "assessability", "") or "") if r1 else "",
            expert_interference=list(getattr(r1, "interference", []) or []) if r1 else [],
            expert_comment=str(getattr(r1, "rationale", "") or "") if r1 else "",
            second_review_id=str(getattr(r2, "review_id", "") or "") if r2 else "",
            second_morphology=str(getattr(r2, "morphology", "") or "") if r2 else "",
            arbitration_id=adj_id,
            candidate_snapshot_hash=str(getattr(snap, "snapshot_hash", "") or "") if snap else "",
            candidate_state=cand_state,
            candidate_strength=str(
                (cmp_row or {}).get("candidate_strength")
                or getattr(snap, "ordinal_strength", "")
                or ""
            ),
            candidate_engine_version=str(
                getattr(snap, "candidate_engine_version", "") or item.candidate_engine_version or ""
            ),
            candidate_ruleset_id=str(
                getattr(snap, "ruleset_id", "") or item.ruleset_id or ""
            ),
            candidate_ruleset_hash=str(
                getattr(snap, "ruleset_hash", "") or item.ruleset_hash or ""
            ),
            geometry_version=str(item.feature_version or ""),
            evidence_categories=_evidence_categories(snap),
            comparison_id=str((cmp_row or {}).get("comparison_id") or ""),
            comparison_status=str((cmp_row or {}).get("agreement_status") or ""),
            post_comparison_note=str((cmp_row or {}).get("comparison_comment") or ""),
            eligibility_bucket=bucket,
            exclusion_reason=exclusion or (bucket if bucket != "eligible_comparable" else ""),
            contamination_status="not_exposed",
            item_status=str(item.item_status or ""),
            available=available,
        )
        # annotate source_date via related fields already on frame_time
        if source_date and not row.frame_time:
            row.frame_time = source_date
        rows.append(row)
        buckets[bucket] += 1

    # Unresolved revision conflicts from projection
    if getattr(proj, "conflicting_item_ids", None):
        for iid in proj.conflicting_item_ids:
            warnings.append(f"unresolved_revision:{cohort_id}:{iid}")
            buckets["unresolved_revision"] += 1

    return rows, dict(buckets), warnings


def check_version_compatibility(rows: list[SnapshotItemRecord]) -> dict[str, Any]:
    engines = sorted({r.candidate_engine_version for r in rows if r.candidate_engine_version})
    rulesets = sorted(
        {
            f"{r.candidate_ruleset_id}:{r.candidate_ruleset_hash}"
            for r in rows
            if r.candidate_ruleset_id or r.candidate_ruleset_hash
        }
    )
    geometries = sorted({r.geometry_version for r in rows if r.geometry_version})
    multi = len(engines) > 1 or len({r.candidate_ruleset_id for r in rows if r.candidate_ruleset_id}) > 1
    warnings: list[str] = []
    if multi:
        warnings.append(
            "Multiple candidate engine/ruleset versions detected; "
            "analyze as separate strata — do not merge into one undifferentiated matrix."
        )
    return {
        "candidate_engine_versions": engines,
        "candidate_ruleset_versions": rulesets,
        "geometry_versions": geometries,
        "version_strata_required": multi,
        "compatibility_warnings": warnings,
    }


def humanize_candidate_label(candidate_state: str) -> str:
    mapped = map_candidate_state_to_human(candidate_state)
    return mapped or candidate_state
