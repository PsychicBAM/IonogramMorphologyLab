"""Guided review workflow stage determination (Phase 4C.2b)."""

from __future__ import annotations

from typing import Any, Literal

from ionogram_morphology_lab.morphology_review_corpus.constants import (
    REVEAL_AFTER_BLIND_LOCK,
    REVEAL_PER_ITEM,
    REVEAL_STRICT_COHORT,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

WorkflowStage = Literal[
    "composition",
    "blind_review",
    "blind_complete",
    "comparison",
    "summary",
]

STAGE_LABELS = {
    "composition": {"en": "Cohort composition", "ru": "Состав корпуса"},
    "blind_review": {"en": "Blind review", "ru": "Слепая оценка"},
    "blind_complete": {"en": "Candidate comparison", "ru": "Сравнение с кандидатом"},
    "comparison": {"en": "Candidate comparison", "ru": "Сравнение с кандидатом"},
    "summary": {"en": "Summary and export", "ru": "Сводка и экспорт"},
}

GUIDED_STEPS = (
    "composition",
    "blind_review",
    "comparison",
    "summary",
)


def normalize_reveal_policy(policy: str | None) -> str:
    p = (policy or REVEAL_STRICT_COHORT).strip()
    if p == REVEAL_AFTER_BLIND_LOCK:
        return REVEAL_PER_ITEM
    if p in (REVEAL_STRICT_COHORT, REVEAL_PER_ITEM):
        return p
    # Unknown → preserve as per-item for safety of older corpora
    return REVEAL_PER_ITEM if p else REVEAL_STRICT_COHORT


def stage_label(stage: str, lang: str = "en") -> str:
    row = STAGE_LABELS.get(stage) or STAGE_LABELS["composition"]
    return row["ru" if lang == "ru" else "en"]


def round1_complete(store: MorphologyReviewCorpusStore, cohort_id: str) -> bool:
    items = [
        it
        for it in store.load_items(cohort_id)
        if it.item_status != "item_unavailable"
    ]
    if not items:
        return False
    for it in items:
        r1 = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        if r1 is None or not r1.locked:
            return False
    return True


def next_unfinished_blind_item(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> str | None:
    for it in sorted(store.load_items(cohort_id), key=lambda x: x.manifest_position):
        if it.item_status == "item_unavailable":
            continue
        r1 = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        if r1 is None or not r1.locked:
            return it.item_id
    return None


def next_uncompared_item(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> str | None:
    from ionogram_morphology_lab.morphology_review_corpus.current_state import (
        next_uncompared_item_current,
    )

    return next_uncompared_item_current(store, cohort_id)


def comparisons_complete(store: MorphologyReviewCorpusStore, cohort_id: str) -> bool:
    from ionogram_morphology_lab.morphology_review_corpus.current_state import (
        comparisons_complete_current,
    )

    return comparisons_complete_current(store, cohort_id)


def determine_workflow_stage(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> dict[str, Any]:
    """Derive guided stage from cohort state and records."""
    manifest = store.load_manifest(cohort_id)
    proto = store.load_protocol(cohort_id)
    policy = normalize_reveal_policy(proto.reveal_policy)
    items = store.load_items(cohort_id)
    n_items = len(items)
    n_r1 = sum(
        1
        for it in items
        if it.item_status != "item_unavailable"
        and (r := store.locked_review_for_item(cohort_id, it.item_id, review_round=1))
        and r.locked
    )
    from ionogram_morphology_lab.morphology_review_corpus.current_state import (
        project_cohort_comparisons,
    )

    cmp_proj = project_cohort_comparisons(store, cohort_id)
    n_cmp = cmp_proj.current_count

    if not manifest.frozen:
        return {
            "stage": "composition",
            "guided_step": "composition",
            "reveal_policy": policy,
            "primary_action": "freeze_and_start",
            "next_item_id": None,
            "counts": {"items": n_items, "round1": n_r1, "comparisons": n_cmp},
        }

    if not round1_complete(store, cohort_id):
        return {
            "stage": "blind_review",
            "guided_step": "blind_review",
            "reveal_policy": policy,
            "primary_action": "save_and_next",
            "next_item_id": next_unfinished_blind_item(store, cohort_id),
            "counts": {"items": n_items, "round1": n_r1, "comparisons": n_cmp},
        }

    # Round-one complete — primary path is batch reveal + automatic comparison.
    if not comparisons_complete(store, cohort_id):
        nxt = next_uncompared_item(store, cohort_id)
        stage_name = "blind_complete" if n_cmp == 0 else "comparison"
        # Strict cohort: one batch action. Per-item: batch still available; per-item
        # inspect mode remains under More → Per-item Comparison.
        primary = "batch_reveal_compare"
        if policy != REVEAL_STRICT_COHORT and n_cmp > 0:
            # Continue remaining via batch (or per-item inspect).
            primary = "batch_reveal_compare"
        return {
            "stage": stage_name,
            "guided_step": "comparison",
            "reveal_policy": policy,
            "primary_action": primary,
            "next_item_id": nxt,
            "counts": {"items": n_items, "round1": n_r1, "comparisons": n_cmp},
        }

    return {
        "stage": "summary",
        "guided_step": "summary",
        "reveal_policy": policy,
        "primary_action": "export_or_validate",
        "next_item_id": None,
        "counts": {"items": n_items, "round1": n_r1, "comparisons": n_cmp},
    }
