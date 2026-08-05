"""Batch candidate reveal + automatic comparison derivation (Phase 4C.3a.2).

Comparison status is deterministic from the locked blind review and the frozen
candidate snapshot via ``comparison_status`` / ``reveal_and_compare``. No new
scientific rules are introduced here.
"""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.constants import REVEAL_STRICT_COHORT
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    project_cohort_comparisons,
)
from ionogram_morphology_lab.morphology_review_corpus.store import (
    BlindRevealError,
    MorphologyReviewCorpusStore,
)
from ionogram_morphology_lab.morphology_review_corpus.workflow import (
    comparisons_complete,
    normalize_reveal_policy,
    round1_complete,
)


class BatchCompareError(RuntimeError):
    """Batch reveal/compare cannot proceed."""


def can_batch_reveal_and_compare(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> dict[str, Any]:
    """Return readiness for the one-shot batch reveal/compare action."""
    proto = store.load_protocol(cohort_id)
    policy = normalize_reveal_policy(proto.reveal_policy)
    items = [
        it
        for it in store.load_items(cohort_id)
        if it.item_status != "item_unavailable"
    ]
    eligible_n = len(items)
    r1_done = round1_complete(store, cohort_id)
    proj = project_cohort_comparisons(store, cohort_id)
    cmp_done = int(proj.current_count)
    complete = comparisons_complete(store, cohort_id)
    # Primary batch action is for strict cohort blinding after full round-1.
    # Per-item cohorts may still use the same batch helper once round-1 is done.
    allowed = bool(r1_done and eligible_n > 0)
    return {
        "allowed": allowed,
        "blocked_reason": (
            ""
            if allowed
            else (
                "blind_round_incomplete"
                if not r1_done
                else "no_eligible_items"
            )
        ),
        "reveal_policy": policy,
        "strict_cohort": policy == REVEAL_STRICT_COHORT,
        "eligible_count": eligible_n,
        "comparisons_current": cmp_done,
        "comparisons_complete": complete,
        "round1_complete": r1_done,
    }


def batch_reveal_and_compare(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Reveal candidates and derive current comparisons for all eligible items.

    Idempotent: repeated invocation does not create duplicate current comparisons
    or inflate progress beyond the eligible item count.
    """
    readiness = can_batch_reveal_and_compare(store, cohort_id)
    if not readiness["allowed"] and not force:
        raise BatchCompareError(readiness["blocked_reason"] or "batch_not_allowed")

    items = sorted(
        (
            it
            for it in store.load_items(cohort_id)
            if it.item_status != "item_unavailable"
        ),
        key=lambda x: x.manifest_position,
    )
    compared: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    reused = 0
    created = 0

    for it in items:
        rev = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        if rev is None or not rev.locked:
            errors.append({"item_id": it.item_id, "reason": "missing_locked_review"})
            continue
        before = store.current_comparison_for_item(cohort_id, it.item_id)
        try:
            cmp = store.reveal_and_compare(
                cohort_id,
                it.item_id,
                review_id=rev.review_id,
                reviewer_note_codes=[],
                comparison_comment="",
            )
        except BlindRevealError as exc:
            errors.append({"item_id": it.item_id, "reason": str(exc)})
            continue
        if before is not None and before.comparison_id == cmp.comparison_id:
            reused += 1
        else:
            created += 1
        row = {
            "item_id": it.item_id,
            "comparison_id": cmp.comparison_id,
            "agreement_status": cmp.agreement_status,
            "source_display_name": it.source_display_name,
            "frame_index": it.frame_index,
        }
        compared.append(row)
        if cmp.agreement_status == "candidate_unavailable":
            unavailable.append(row)

    proj = project_cohort_comparisons(store, cohort_id)
    eligible_n = len(items)
    current_n = int(proj.current_count)
    if current_n > eligible_n:
        raise BatchCompareError(
            f"comparison_count_exceeds_eligible:{current_n}>{eligible_n}"
        )

    return {
        "ok": not errors,
        "cohort_id": cohort_id,
        "eligible_count": eligible_n,
        "compared_count": current_n,
        "unavailable_count": len(unavailable),
        "created_count": created,
        "reused_count": reused,
        "history_rows": len(proj.history_rows),
        "compared": compared,
        "unavailable": unavailable,
        "errors": errors,
        "open_summary": current_n >= eligible_n and eligible_n > 0,
        "message_en": _batch_message_en(current_n, eligible_n, len(unavailable)),
        "message_ru": _batch_message_ru(current_n, eligible_n, len(unavailable)),
    }


def _batch_message_en(compared: int, eligible: int, unavailable: int) -> str:
    if unavailable:
        return (
            f"Compared {compared} of {eligible}; "
            f"candidate unavailable for {unavailable} frame(s)."
        )
    return f"Compared {compared} of {eligible}."


def _batch_message_ru(compared: int, eligible: int, unavailable: int) -> str:
    if unavailable:
        return (
            f"Сравнено {compared} из {eligible}; "
            f"для {unavailable} кадров кандидат недоступен."
        )
    return f"Сравнено {compared} из {eligible}."
