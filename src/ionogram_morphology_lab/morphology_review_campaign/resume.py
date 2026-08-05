"""Campaign Resume Work routing (Phase 4C.3)."""

from __future__ import annotations

from typing import Any, Literal

from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.morphology_review_corpus.workflow import determine_workflow_stage

ResumeAction = Literal[
    "no_cohort",
    "composition",
    "first_blind_review",
    "comparison",
    "second_review",
    "adjudication",
    "summary_export",
]


def resume_work(
    store: MorphologyReviewCampaignStore,
    campaign_id: str,
    *,
    second_review_assigned: bool | None = None,
    adjudication_required: bool = False,
) -> dict[str, Any]:
    """Determine the next appropriate campaign task.

    Priority:
    1. unfinished first blind review
    2. unfinished comparison after blind-round completion
    3. second-review only when explicitly assigned
    4. adjudication only when explicitly required
    5. summary/export when complete
    """
    prog = campaign_progress(store, campaign_id)
    links = store.list_cohort_links(campaign_id)
    if not links:
        return {
            "action": "no_cohort",
            "cohort_id": None,
            "item_id": None,
            "tab_hint": "campaigns",
            "message_en": "No linked cohort. Create or link a cohort first.",
            "message_ru": "Нет связанного корпуса. Сначала создайте или привяжите корпус.",
            "progress": prog,
        }

    # Prefer first_review role cohort
    first_link = next(
        (L for L in links if L.cohort_role == "first_review"), links[0]
    )
    cohort_id = first_link.cohort_id
    stage = determine_workflow_stage(store.corpus, cohort_id)
    assignments = store.list_assignments(campaign_id)
    if second_review_assigned is None:
        second_review_assigned = any(a.role == "second_reviewer" for a in assignments)

    # 1. Blind
    if stage["stage"] in ("composition",):
        return {
            "action": "composition",
            "cohort_id": cohort_id,
            "item_id": None,
            "tab_hint": "guided",
            "primary_action": stage.get("primary_action"),
            "message_en": "Freeze the linked cohort to begin blind review.",
            "message_ru": "Зафиксируйте связанный корпус, чтобы начать слепую оценку.",
            "progress": prog,
            "workflow_stage": stage,
        }

    if stage["stage"] == "blind_review":
        return {
            "action": "first_blind_review",
            "cohort_id": cohort_id,
            "item_id": stage.get("next_item_id"),
            "tab_hint": "rapid",
            "primary_action": stage.get("primary_action"),
            "message_en": "Resume unfinished first blind review.",
            "message_ru": "Продолжить незавершённую первую слепую оценку.",
            "progress": prog,
            "workflow_stage": stage,
        }

    # 2. Batch reveal + automatic comparison (after blind round complete)
    if stage["stage"] in ("blind_complete", "comparison"):
        return {
            "action": "batch_reveal_compare",
            "cohort_id": cohort_id,
            "item_id": stage.get("next_item_id"),
            "tab_hint": "guided",
            "primary_action": "batch_reveal_compare",
            "message_en": (
                "Blind review is complete. Reveal candidates and calculate comparisons "
                "in one step. Locked blind reviews will not change."
            ),
            "message_ru": (
                "Слепая оценка завершена. Покажите кандидатов и рассчитайте сравнения "
                "одним действием. Зафиксированные слепые оценки не изменятся."
            ),
            "progress": prog,
            "workflow_stage": stage,
        }

    # 3. Optional second review — only if assigned and incomplete
    if second_review_assigned:
        second_pending = None
        for it in store.corpus.load_items(cohort_id):
            if it.item_status == "item_unavailable":
                continue
            r1 = store.corpus.locked_review_for_item(cohort_id, it.item_id, review_round=1)
            r2 = store.corpus.locked_review_for_item(cohort_id, it.item_id, review_round=2)
            if r1 and (r2 is None or not r2.locked):
                second_pending = it.item_id
                break
        if second_pending:
            return {
                "action": "second_review",
                "cohort_id": cohort_id,
                "item_id": second_pending,
                "tab_hint": "review",
                "primary_action": "second_blind_review",
                "message_en": (
                    "Second independent review is assigned and unfinished "
                    "(optional research track)."
                ),
                "message_ru": (
                    "Назначена и не завершена вторая независимая оценка "
                    "(дополнительное исследование)."
                ),
                "progress": prog,
                "workflow_stage": stage,
            }

    # 4. Adjudication only when required
    if adjudication_required:
        return {
            "action": "adjudication",
            "cohort_id": cohort_id,
            "item_id": None,
            "tab_hint": "summary",
            "primary_action": "adjudicate",
            "message_en": "Adjudication required for independent reviewer disagreement.",
            "message_ru": "Требуется арбитраж при расхождении независимых экспертов.",
            "progress": prog,
            "workflow_stage": stage,
        }

    # 5. Complete
    return {
        "action": "summary_export",
        "cohort_id": cohort_id,
        "item_id": None,
        "tab_hint": "summary",
        "primary_action": "export_or_validate",
        "message_en": "Campaign work complete — open summary and export readiness report.",
        "message_ru": "Работа кампании завершена — откройте сводку и экспорт готовности.",
        "progress": prog,
        "workflow_stage": stage,
    }
