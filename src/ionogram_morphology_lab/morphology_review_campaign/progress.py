"""Campaign progress from authoritative current-state projections (Phase 4C.3)."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    count_consistency,
    project_cohort_comparisons,
)
from ionogram_morphology_lab.morphology_review_corpus.workflow import (
    next_uncompared_item,
    next_unfinished_blind_item,
    round1_complete,
)


def _unique_item_key(cohort_id: str, item_id: str) -> str:
    return f"{cohort_id}:{item_id}"


def campaign_progress(store: MorphologyReviewCampaignStore, campaign_id: str) -> dict[str, Any]:
    """Aggregate progress across linked cohorts using current-state counts only."""
    manifest = store.load_manifest(campaign_id)
    links = store.list_cohort_links(campaign_id)
    planned = int(manifest.target_review_count or 0)
    unique_items: set[str] = set()
    eligible_items: set[str] = set()
    unique_fps: set[str] = set()
    r1_done = 0
    r2_done = 0
    cmp_done = 0
    adj_done = 0
    unavailable = 0
    blocked: list[dict[str, Any]] = []
    integrity_ok = True
    integrity_messages: list[str] = []
    per_cohort: list[dict[str, Any]] = []

    for link in links:
        cid = link.cohort_id
        if cid not in store.corpus.list_cohorts():
            integrity_ok = False
            integrity_messages.append(f"Missing linked cohort: {cid}")
            continue
        cm = store.corpus.load_manifest(cid)
        if cm.manifest_hash != link.manifest_hash and cm.frozen:
            # Draft/revision may rehash; warn if frozen hash drifts
            integrity_messages.append(
                f"Manifest hash drift for {cid}: linked={link.manifest_hash[:12]}… "
                f"current={cm.manifest_hash[:12]}…"
            )
        items = store.corpus.load_items(cid)
        cmp_proj = project_cohort_comparisons(store.corpus, cid)
        consistency = count_consistency(store.corpus, cid)
        if not consistency.get("ok", True):
            integrity_ok = False
            integrity_messages.extend(consistency.get("messages") or [])

        cohort_r1 = 0
        cohort_r2 = 0
        eligible_n = 0
        for it in items:
            key = _unique_item_key(cid, it.item_id)
            unique_items.add(key)
            unique_fps.add(f"{it.source_sha256}:{it.frame_index}")
            if it.item_status == "item_unavailable":
                unavailable += 1
                blocked.append(
                    {
                        "cohort_id": cid,
                        "item_id": it.item_id,
                        "reason": it.unavailable_reason or "unavailable",
                        "kind": "permanently_excluded"
                        if it.unavailable_reason
                        in ("source_missing", "invalid_source_sha256", "source_unavailable")
                        else "temporarily_blocked",
                    }
                )
                continue
            eligible_items.add(key)
            eligible_n += 1
            r1 = store.corpus.locked_review_for_item(cid, it.item_id, review_round=1)
            if r1 and r1.locked:
                cohort_r1 += 1
                r1_done += 1
            r2 = store.corpus.locked_review_for_item(cid, it.item_id, review_round=2)
            if r2 and r2.locked:
                # Same-reviewer repeat is not independent — still count as record but flag
                if r1 and r2.reviewer_id == r1.reviewer_id:
                    blocked.append(
                        {
                            "cohort_id": cid,
                            "item_id": it.item_id,
                            "reason": "same_reviewer_repeat_not_independent",
                            "kind": "pending_preparation",
                        }
                    )
                else:
                    cohort_r2 += 1
                    r2_done += 1
            if it.item_status == "adjudication_locked":
                adj_done += 1

        # Current comparisons only — never raw JSONL length
        cohort_cmp = cmp_proj.current_count
        cmp_done += cohort_cmp
        if cmp_proj.current_count > eligible_n:
            integrity_ok = False
            integrity_messages.append(
                f"Comparison current count exceeds eligible items in {cid}"
            )
        # Detect raw-history overcount risk
        history_n = len(cmp_proj.history_rows)
        if history_n > cmp_proj.current_count:
            # Not an error if current projection is correct — informational
            pass
        per_cohort.append(
            {
                "cohort_id": cid,
                "cohort_role": link.cohort_role,
                "items": len(items),
                "eligible": eligible_n,
                "round1": cohort_r1,
                "round2": cohort_r2,
                "comparisons_current": cohort_cmp,
                "comparisons_history": history_n,
                "next_blind": next_unfinished_blind_item(store.corpus, cid),
                "next_compare": next_uncompared_item(store.corpus, cid),
                "round1_complete": round1_complete(store.corpus, cid),
            }
        )

    eligible_n = len(eligible_items)
    return {
        "campaign_id": campaign_id,
        "state": manifest.state,
        "planned_items": planned,
        "unique_real_items": eligible_n,
        "unique_source_frame_fingerprints": len(unique_fps),
        "actual_item_count": int(manifest.actual_item_count or eligible_n),
        "first_blind_progress": {"completed": r1_done, "total": eligible_n},
        "comparison_progress": {"completed": cmp_done, "total": eligible_n},
        "second_review_progress": {"completed": r2_done, "total": eligible_n},
        "adjudication_progress": {"completed": adj_done, "total": eligible_n},
        "unavailable_items": unavailable,
        "blocked_items": blocked,
        "integrity_ok": integrity_ok,
        "integrity_messages": integrity_messages,
        "per_cohort": per_cohort,
        "second_reviewer_optional": bool(
            (manifest.reviewer_plan or {}).get("second_reviewer_optional", True)
        ),
        # Invariant helpers
        "invariants": {
            "comparisons_le_unique": cmp_done <= eligible_n,
            "round1_le_unique": r1_done <= eligible_n,
            "second_le_unique": r2_done <= eligible_n,
        },
    }
