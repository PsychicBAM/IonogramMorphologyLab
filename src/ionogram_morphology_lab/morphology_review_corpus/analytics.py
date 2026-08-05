"""Descriptive analytics only — no accuracy / F1 / validated performance."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.constants import PROHIBITED_METRICS
from ionogram_morphology_lab.morphology_review_corpus.labels import assert_no_prohibited_metrics
from ionogram_morphology_lab.morphology_review_corpus.models import BlindReviewRecord
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def descriptive_summary(store: MorphologyReviewCorpusStore, cohort_id: str) -> dict[str, Any]:
    items = store.load_items(cohort_id)
    manifest = store.load_manifest(cohort_id)
    availability = Counter(it.item_status for it in items)
    reviews_r1: list[BlindReviewRecord] = []
    reviews_r2: list[BlindReviewRecord] = []
    for it in items:
        r1 = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        r2 = store.locked_review_for_item(cohort_id, it.item_id, review_round=2)
        if r1:
            reviews_r1.append(r1)
        if r2:
            reviews_r2.append(r2)

    human_labels = Counter(r.morphology for r in reviews_r1)
    assessability = Counter(r.assessability for r in reviews_r1)
    interference = Counter()
    for r in reviews_r1:
        for flag in r.interference:
            interference[flag] += 1
    abstention = sum(
        1 for r in reviews_r1 if r.morphology in ("indeterminate", "not_assessable")
    )

    from ionogram_morphology_lab.morphology_review_corpus.current_state import (
        count_consistency,
        project_cohort_comparisons,
    )

    cmp_proj = project_cohort_comparisons(store, cohort_id)
    comparisons = cmp_proj.current_rows
    agreement = Counter(c.get("agreement_status") for c in comparisons)
    exact = int(agreement.get("exact_agreement") or 0)
    cand_labels = Counter(c.get("candidate_state") for c in comparisons if c.get("candidate_state"))
    cand_abstain = sum(
        1
        for c in comparisons
        if c.get("agreement_status") in ("candidate_abstained", "both_abstained")
    )

    # Disagreement matrix (human vs candidate morphology codes) — current only
    matrix: dict[str, dict[str, int]] = {}
    for c in comparisons:
        h = str(c.get("human_morphology") or "")
        cand = str(c.get("candidate_state") or "")
        matrix.setdefault(h, {})
        matrix[h][cand] = matrix[h].get(cand, 0) + 1

    # Inter-reviewer agreement only with genuinely independent reviews
    inter = inter_reviewer_descriptive(store, cohort_id)

    adjudications = store._read_jsonl(store.path_for(cohort_id) / "adjudications.jsonl")
    # One adjudication per item (latest)
    adj_by_item: dict[str, dict[str, Any]] = {}
    for adj in adjudications:
        iid = str(adj.get("item_id") or "")
        if iid:
            adj_by_item[iid] = adj
    consistency = count_consistency(store, cohort_id)

    summary: dict[str, Any] = {
        "kind": "descriptive_summary",
        "scientific_claim": "none",
        "note_en": (
            "Descriptive counts only. Not accuracy, precision, recall, sensitivity, "
            "specificity, or F1. Pilot corpus is not a scientific validation set. "
            "Comparison statuses are derived automatically from locked blind reviews "
            "and frozen candidate results; they are not a judgment of truth for either "
            "the expert or the automatic decision."
        ),
        "note_ru": (
            "Только описательные счётчики. Не accuracy/precision/recall/sensitivity/"
            "specificity/F1. Пилотный корпус — не научно валидированный набор. "
            "Статусы сравнения рассчитаны автоматически на основе зафиксированных "
            "слепых оценок и замороженных результатов кандидата. Они не являются "
            "оценкой истинности экспертного или автоматического решения."
        ),
        "auto_compare_note_en": (
            "Comparison statuses are derived automatically from locked blind reviews "
            "and frozen candidate results. They are not a judgment of truth for either "
            "the expert or the automatic decision."
        ),
        "auto_compare_note_ru": (
            "Статусы сравнения рассчитаны автоматически на основе зафиксированных "
            "слепых оценок и замороженных результатов кандидата. Они не являются "
            "оценкой истинности экспертного или автоматического решения."
        ),
        "cohort_id": cohort_id,
        "manifest_hash": manifest.manifest_hash,
        "item_count": len(items),
        "availability_counts": dict(availability),
        "completed_blind_reviews_round1": len(reviews_r1),
        "completed_blind_reviews_round2": len(reviews_r2),
        "human_label_distribution": dict(human_labels),
        "candidate_label_distribution_after_reveal": dict(cand_labels),
        "assessability_distribution": dict(assessability),
        "interference_distribution": dict(interference),
        "human_abstention_count": abstention,
        "human_abstention_rate": (abstention / len(reviews_r1)) if reviews_r1 else None,
        "candidate_abstention_count": cand_abstain,
        "exact_agreement_count": exact,
        "exact_agreement_proportion": (exact / len(comparisons)) if comparisons else None,
        "agreement_status_counts": dict(agreement),
        "disagreement_matrix": matrix,
        "review_completion_progress": {
            "items": len(items),
            "round1_locked": len(reviews_r1),
            "round2_locked": len(reviews_r2),
            "comparisons": len(comparisons),
            "comparisons_history_rows": len(cmp_proj.history_rows),
            "adjudications": len(adj_by_item),
        },
        "second_review_agreement": inter,
        "adjudication_count": len(adj_by_item),
        "count_consistency": consistency,
        "second_reviewer_optional_note_en": (
            "A second independent reviewer is not required for human-versus-candidate "
            "comparison. It is only needed for inter-reviewer agreement and possible "
            "adjudication."
        ),
        "second_reviewer_optional_note_ru": (
            "Второй независимый эксперт не обязателен для сравнения с кандидатом. "
            "Он нужен только для оценки межэкспертного согласия и возможного арбитража."
        ),
        "prohibited_metrics": sorted(PROHIBITED_METRICS),
    }
    assert_no_prohibited_metrics(summary)
    return summary


def inter_reviewer_descriptive(
    store: MorphologyReviewCorpusStore, cohort_id: str
) -> dict[str, Any]:
    """Descriptive pairwise agreement; undefined when insufficient independent variation."""
    pairs = []
    for it in store.load_items(cohort_id):
        r1 = store.locked_review_for_item(cohort_id, it.item_id, review_round=1)
        r2 = store.locked_review_for_item(cohort_id, it.item_id, review_round=2)
        if not r1 or not r2:
            continue
        if r1.reviewer_id == r2.reviewer_id:
            continue
        if r1.superseded or r2.superseded:
            continue
        pairs.append((r1.morphology, r2.morphology))
    if len(pairs) < 2:
        return {
            "method": "descriptive_exact_match_rate",
            "defined": False,
            "reason": "Fewer than two independent dual-reviewed items",
            "n_pairs": len(pairs),
            "exact_match_count": None,
            "exact_match_rate": None,
        }
    labels = {a for pair in pairs for a in pair}
    if len(labels) < 2:
        return {
            "method": "descriptive_exact_match_rate",
            "defined": False,
            "reason": "No class variation among dual-reviewed items",
            "n_pairs": len(pairs),
            "exact_match_count": None,
            "exact_match_rate": None,
        }
    matches = sum(1 for a, b in pairs if a == b)
    return {
        "method": "descriptive_exact_match_rate",
        "defined": True,
        "descriptive_only": True,
        "n_pairs": len(pairs),
        "exact_match_count": matches,
        "exact_match_rate": matches / len(pairs),
        "note": "Not Cohen kappa; not a validation claim.",
    }


def refuse_unsupported_metrics(requested: list[str]) -> dict[str, Any]:
    bad = [m for m in requested if m.lower() in PROHIBITED_METRICS]
    return {
        "ok": False,
        "refused": bad,
        "message_en": (
            "Phase 4C.2 does not export accuracy, precision, recall, sensitivity, "
            "specificity, or F1. Those require a later approved reference-standard protocol."
        ),
        "message_ru": (
            "Фаза 4C.2 не экспортирует accuracy/precision/recall/sensitivity/specificity/F1. "
            "Для этого нужен позднее утверждённый протокол эталона."
        ),
    }
