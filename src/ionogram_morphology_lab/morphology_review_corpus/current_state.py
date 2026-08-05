"""Authoritative current-state projection for review corpora (Phase 4C.2b.3).

Append-only JSONL history remains complete. Dashboards, Guided progress, and
Summary distributions must use *current* non-superseded records per item —
never raw row counts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

COMPARISON_CONTRACT_VERSION = 1


@dataclass
class ComparisonProjection:
    """One current comparison (or none) per item, plus repair diagnostics."""

    current_by_item: dict[str, dict[str, Any]] = field(default_factory=dict)
    history_rows: list[dict[str, Any]] = field(default_factory=list)
    duplicate_item_ids: list[str] = field(default_factory=list)
    identical_duplicate_ids: list[str] = field(default_factory=list)
    conflicting_item_ids: list[str] = field(default_factory=list)
    superseded_ids: list[str] = field(default_factory=list)
    invariant_ok: bool = True
    invariant_messages: list[str] = field(default_factory=list)

    @property
    def current_rows(self) -> list[dict[str, Any]]:
        return list(self.current_by_item.values())

    @property
    def current_count(self) -> int:
        return len(self.current_by_item)


def _logical_comparison_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("cohort_id") or ""),
        str(row.get("item_id") or ""),
        str(row.get("review_id") or ""),
        str(row.get("candidate_state") or ""),
        str(row.get("agreement_status") or ""),
    )


def _content_fingerprint(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("review_id"),
        row.get("human_morphology"),
        row.get("candidate_state"),
        row.get("candidate_strength"),
        row.get("agreement_status"),
        tuple(row.get("reviewer_note_codes") or []),
        (row.get("comparison_comment") or "").strip(),
    )


def project_comparisons(
    rows: list[dict[str, Any]],
    *,
    eligible_item_ids: list[str] | None = None,
) -> ComparisonProjection:
    """Project append-only comparison history to one current row per item_id.

    Rules:
    - Rows superseded via ``supersedes_comparison_id`` chains are non-current.
    - Legacy duplicates (no chain): keep the last file-order row per item as current.
    - Identical duplicates are reported; conflicting content is reported separately.
    """
    proj = ComparisonProjection(history_rows=list(rows))
    if not rows:
        return proj

    # Build explicit supersession graph when linkage fields exist.
    superseded: set[str] = set()
    by_id = {str(r.get("comparison_id") or ""): r for r in rows if r.get("comparison_id")}
    for r in rows:
        prior = str(r.get("supersedes_comparison_id") or r.get("prior_comparison_id") or "")
        if prior and prior in by_id:
            superseded.add(prior)
    proj.superseded_ids = sorted(superseded)

    # Group by item_id preserving file order.
    by_item: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        iid = str(r.get("item_id") or "")
        if not iid:
            continue
        by_item.setdefault(iid, []).append(r)

    for iid, group in by_item.items():
        active = [
            r
            for r in group
            if str(r.get("comparison_id") or "") not in superseded
            and not r.get("non_current")
            and not r.get("repair_non_current")
        ]
        if not active:
            # All marked superseded — fall back to last row.
            active = group[-1:]
        if len(group) > 1:
            proj.duplicate_item_ids.append(iid)
        fingerprints = {_content_fingerprint(r) for r in group}
        if len(group) > 1 and len(fingerprints) == 1:
            proj.identical_duplicate_ids.append(iid)
        elif len(group) > 1 and len(fingerprints) > 1:
            # Conflicting only if more than one active without explicit chain.
            chained = any(
                r.get("supersedes_comparison_id") or r.get("prior_comparison_id") or r.get("revision_reason")
                for r in group
            )
            if not chained and len(active) > 1:
                proj.conflicting_item_ids.append(iid)
        # Current = last active in file order (latest append).
        proj.current_by_item[iid] = active[-1]

    if eligible_item_ids is not None:
        n_elig = len(eligible_item_ids)
        if proj.current_count > n_elig:
            proj.invariant_ok = False
            proj.invariant_messages.append(
                f"current_comparisons={proj.current_count} exceeds eligible_items={n_elig}"
            )
        if len(rows) > n_elig and proj.duplicate_item_ids:
            # History may exceed; current must not.
            pass
    return proj


def project_cohort_comparisons(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> ComparisonProjection:
    items = store.load_items(cohort_id)
    eligible = [it.item_id for it in items if it.item_status != "item_unavailable"]
    rows = store._read_jsonl(store.path_for(cohort_id) / "reveal_comparisons.jsonl")
    return project_comparisons(rows, eligible_item_ids=eligible)


def current_comparison_for_item(
    store: MorphologyReviewCorpusStore, cohort_id: str, item_id: str
) -> dict[str, Any] | None:
    return project_cohort_comparisons(store, cohort_id).current_by_item.get(item_id)


def comparisons_complete_current(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> bool:
    from ionogram_morphology_lab.morphology_review_corpus.workflow import round1_complete

    if not round1_complete(store, cohort_id):
        return False
    items = [
        it
        for it in store.load_items(cohort_id)
        if it.item_status != "item_unavailable"
    ]
    proj = project_cohort_comparisons(store, cohort_id)
    return all(it.item_id in proj.current_by_item for it in items)


def next_uncompared_item_current(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> str | None:
    proj = project_cohort_comparisons(store, cohort_id)
    for it in sorted(store.load_items(cohort_id), key=lambda x: x.manifest_position):
        if it.item_status == "item_unavailable":
            continue
        r1 = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        if r1 is None or not r1.locked:
            continue
        if it.item_id not in proj.current_by_item:
            return it.item_id
    return None


def count_consistency(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> dict[str, Any]:
    """Verify dashboard invariants from current-state projection."""
    items = store.load_items(cohort_id)
    n_items = len(items)
    n_elig = sum(1 for it in items if it.item_status != "item_unavailable")
    n_r1 = sum(
        1
        for it in items
        if it.item_status != "item_unavailable"
        and (r := store.locked_review_for_item(cohort_id, it.item_id, review_round=1))
        and r.locked
    )
    proj = project_cohort_comparisons(store, cohort_id)
    history_n = len(proj.history_rows)
    current_n = proj.current_count
    agreement = Counter(r.get("agreement_status") for r in proj.current_rows)
    cand = Counter(
        r.get("candidate_state") for r in proj.current_rows if r.get("candidate_state")
    )
    ok = (
        0 <= n_r1 <= n_elig <= n_items
        and 0 <= current_n <= n_elig
        and sum(agreement.values()) == current_n
        and sum(cand.values()) <= current_n
        and current_n <= n_elig
    )
    messages = list(proj.invariant_messages)
    if current_n > n_elig:
        messages.append(f"comparisons_current={current_n} > eligible={n_elig}")
    if history_n > current_n and not proj.duplicate_item_ids and history_n > n_elig:
        messages.append(
            f"history_rows={history_n} exceeds items; duplicates may need repair"
        )
    if proj.duplicate_item_ids and history_n > n_elig:
        # Duplicate history is expected after repair projection, but warn if
        # UI would have used raw counts.
        messages.append(
            f"raw_history_rows={history_n} for {n_items} items "
            f"(current={current_n}; duplicates={len(proj.duplicate_item_ids)})"
        )
    # Invariant for display: never show raw>eligible as valid progress.
    display_ok = current_n <= n_elig and n_r1 <= n_elig
    return {
        "ok": ok and display_ok and not proj.conflicting_item_ids,
        "item_count": n_items,
        "eligible_count": n_elig,
        "round1_current": n_r1,
        "comparisons_history": history_n,
        "comparisons_current": current_n,
        "agreement_total": sum(agreement.values()),
        "candidate_label_total": sum(cand.values()),
        "duplicate_item_ids": list(proj.duplicate_item_ids),
        "identical_duplicate_ids": list(proj.identical_duplicate_ids),
        "conflicting_item_ids": list(proj.conflicting_item_ids),
        "messages": messages,
    }


def repair_comparison_derived_state(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    dry_run: bool = True,
    resolve_conflicts: str = "latest_valid",
) -> dict[str, Any]:
    """Repair derived comparison state without deleting history.

    Writes append-only ``comparison_current_state.json`` projection metadata and
    audit events. Identical duplicates keep the last row as current. Conflicting
    duplicates use ``resolve_conflicts`` policy (default: latest file-order) and
    are reported explicitly.
    """
    import json
    from datetime import datetime, timezone

    from ionogram_morphology_lab.morphology_review_corpus.models import AuditEvent

    before = count_consistency(store, cohort_id)
    proj = project_cohort_comparisons(store, cohort_id)
    report = {
        "cohort_id": cohort_id,
        "dry_run": dry_run,
        "resolve_conflicts": resolve_conflicts,
        "before": before,
        "history_rows": len(proj.history_rows),
        "current_count": proj.current_count,
        "identical_duplicates": list(proj.identical_duplicate_ids),
        "conflicting_items": list(proj.conflicting_item_ids),
        "duplicate_items": list(proj.duplicate_item_ids),
        "current_comparison_ids": {
            iid: row.get("comparison_id") for iid, row in proj.current_by_item.items()
        },
        "non_current_comparison_ids": [],
    }
    current_ids = {str(r.get("comparison_id")) for r in proj.current_rows}
    for row in proj.history_rows:
        cid = str(row.get("comparison_id") or "")
        if cid and cid not in current_ids:
            report["non_current_comparison_ids"].append(cid)

    if dry_run:
        report["applied"] = False
        return report

    path = store.path_for(cohort_id) / "comparison_current_state.json"
    payload = {
        "schema": "iml-comparison-current-state-1",
        "repaired_at": datetime.now(timezone.utc).isoformat(),
        "resolve_conflicts": resolve_conflicts,
        "current_by_item": {
            iid: {
                "comparison_id": row.get("comparison_id"),
                "record_hash": row.get("record_hash"),
                "agreement_status": row.get("agreement_status"),
            }
            for iid, row in proj.current_by_item.items()
        },
        "non_current_comparison_ids": report["non_current_comparison_ids"],
        "identical_duplicate_item_ids": report["identical_duplicates"],
        "conflicting_item_ids": report["conflicting_items"],
        "history_row_count": len(proj.history_rows),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    store.append_audit(
        cohort_id,
        AuditEvent.create(
            "comparison_derived_state_repair",
            cohort_id=cohort_id,
            details={
                "history_rows": len(proj.history_rows),
                "current_count": proj.current_count,
                "identical_duplicates": len(proj.identical_duplicate_ids),
                "conflicts": len(proj.conflicting_item_ids),
            },
        ),
    )
    after = count_consistency(store, cohort_id)
    report["after"] = after
    report["applied"] = True
    return report
