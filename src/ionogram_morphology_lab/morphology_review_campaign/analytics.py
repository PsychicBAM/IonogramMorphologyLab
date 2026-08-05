"""Descriptive campaign summaries — no accuracy/F1 (Phase 4C.3)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.constants import PROHIBITED_METRICS
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.labels import assert_no_prohibited_metrics


def campaign_descriptive_summary(
    store: MorphologyReviewCampaignStore, campaign_id: str
) -> dict[str, Any]:
    manifest = store.load_manifest(campaign_id)
    protocol = store.load_protocol(campaign_id)
    prog = campaign_progress(store, campaign_id)
    links = store.list_cohort_links(campaign_id)

    human = Counter()
    cand = Counter()
    assess = Counter()
    interf = Counter()
    agreement = Counter()
    coverage_sources: set[str] = set()
    coverage_dates: set[str] = set()
    coverage_times: set[str] = set()

    for link in links:
        if link.cohort_id not in store.corpus.list_cohorts():
            continue
        s = descriptive_summary(store.corpus, link.cohort_id)
        human.update(s.get("human_label_distribution") or {})
        cand.update(s.get("candidate_label_distribution_after_reveal") or {})
        assess.update(s.get("assessability_distribution") or {})
        interf.update(s.get("interference_distribution") or {})
        agreement.update(s.get("agreement_status_counts") or {})
        for it in store.corpus.load_items(link.cohort_id):
            coverage_sources.add(it.source_display_name or it.source_sha256[:12])
            if it.datetime_metadata:
                coverage_dates.add(it.datetime_metadata)
            if it.frame_time:
                coverage_times.add(it.frame_time)

    summary: dict[str, Any] = {
        "kind": "campaign_descriptive_summary",
        "scientific_claim": "none",
        "note_en": (
            "Descriptive campaign counts only. Not accuracy, precision, recall, "
            "sensitivity, specificity, or F1. Pilot campaign is not a scientific "
            "validation study."
        ),
        "note_ru": (
            "Только описательные счётчики кампании. Не accuracy/precision/recall/"
            "sensitivity/specificity/F1. Пилотная кампания — не научная валидация."
        ),
        "campaign_id": campaign_id,
        "campaign_hash": manifest.campaign_hash,
        "protocol_hash": protocol.protocol_hash,
        "designation_en": manifest.designation_en,
        "designation_ru": manifest.designation_ru,
        "state": manifest.state,
        "planned_items": prog["planned_items"],
        "actual_unique_items": prog["unique_real_items"],
        "completed_blind_reviews": prog["first_blind_progress"]["completed"],
        "completed_comparisons": prog["comparison_progress"]["completed"],
        "optional_second_reviews": prog["second_review_progress"]["completed"],
        "adjudications": prog["adjudication_progress"]["completed"],
        "unavailable_items": prog["unavailable_items"],
        "human_morphology_distribution": dict(human),
        "candidate_morphology_distribution_after_reveal": dict(cand),
        "assessability_distribution": dict(assess),
        "interference_distribution": dict(interf),
        "agreement_status_distribution": dict(agreement),
        "coverage": {
            "sources": sorted(coverage_sources),
            "dates": sorted(coverage_dates),
            "times": sorted(coverage_times),
            "time_windows": list(manifest.time_windows or []),
        },
        "integrity_ok": prog["integrity_ok"],
        "integrity_messages": prog["integrity_messages"],
        "second_reviewer_optional": prog["second_reviewer_optional"],
        "second_reviewer_optional_note_en": (
            "A second independent reviewer is not required for human-versus-candidate "
            "comparison. It is only needed for inter-reviewer agreement and possible "
            "adjudication."
        ),
        "second_reviewer_optional_note_ru": (
            "Второй независимый эксперт не обязателен для сравнения с кандидатом. "
            "Он нужен только для оценки межэкспертного согласия и возможного арбитража."
        ),
        "shadow_only": True,
        "scientifically_validated": False,
        "prohibited_metrics": sorted(PROHIBITED_METRICS),
        "build_identity": manifest.build_identity,
    }
    assert_no_prohibited_metrics(summary)
    return summary


def explain_metrics_unavailable(lang: str = "en") -> str:
    if lang == "ru":
        return (
            "Показатели accuracy/F1/sensitivity/specificity недоступны в этой фазе: "
            "пилотная кампания описательная, кандидат остаётся в shadow-only режиме, "
            "и ни один эксперт не считается ground truth."
        )
    return (
        "Accuracy/F1/sensitivity/specificity are unavailable in this phase: "
        "the pilot campaign is descriptive only, the candidate remains shadow-only, "
        "and no reviewer is treated as ground truth."
    )
