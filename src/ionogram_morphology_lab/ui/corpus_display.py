"""Localized display helpers for Expert Review Corpus (Phase 4C.2b)."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    comparison_status_display,
    display_label,
    morphology_label,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.morphology_review_corpus.workflow import (
    STAGE_LABELS,
    determine_workflow_stage,
    stage_label,
)


def format_comparison_cards(
    *,
    human_morphology: str,
    candidate_state: str | None,
    ordinal_strength: str | None,
    agreement_status: str | None,
    engine: str | None,
    lang: str = "en",
) -> str:
    """Human-readable comparison text — no raw codes in normal view."""
    if lang == "ru":
        lines = [
            "Экспертная оценка:",
            display_label(human_morphology, "ru"),
            "",
            "Предварительный кандидат:",
            display_label(candidate_state or "", "ru") if candidate_state else "—",
            "",
            "Сила поддержки:",
            display_label(ordinal_strength or "", "ru") if ordinal_strength else "—",
            "",
            "Результат сравнения:",
            comparison_status_display(agreement_status, "ru")
            if agreement_status else "Ожидает сохранения сравнения",
            "",
            "Технические сведения:",
            f"Движок: {engine or '—'}",
        ]
    else:
        lines = [
            "Expert assessment:",
            display_label(human_morphology, "en"),
            "",
            "Preliminary candidate:",
            display_label(candidate_state or "", "en") if candidate_state else "—",
            "",
            "Support strength:",
            display_label(ordinal_strength or "", "en") if ordinal_strength else "—",
            "",
            "Comparison result:",
            comparison_status_display(agreement_status, "en")
            if agreement_status else "Awaiting comparison save",
            "",
            "Technical details:",
            f"Engine: {engine or '—'}",
        ]
    return "\n".join(lines)


def format_summary_dashboard(
    store: MorphologyReviewCorpusStore, cohort_id: str, lang: str = "en"
) -> str:
    """Human-readable Summary — not raw JSON."""
    s = descriptive_summary(store, cohort_id)
    inter = s.get("second_review_agreement") or {}
    progress = s.get("review_completion_progress") or {}
    items = int(s.get("item_count") or 0)
    r1 = int(s.get("completed_blind_reviews_round1") or 0)
    pending = max(0, items - r1)
    cmp_n = int(progress.get("comparisons") or 0)
    r2 = int(s.get("completed_blind_reviews_round2") or 0)
    adj = int(s.get("adjudication_count") or 0)
    consistency = s.get("count_consistency") or {}
    history_rows = int(progress.get("comparisons_history_rows") or 0)

    def _dist(d: dict[str, Any]) -> str:
        if not d:
            return "—"
        parts = []
        for k, v in sorted(d.items(), key=lambda kv: (-int(kv[1]), str(kv[0]))):
            try:
                lab = (
                    comparison_status_display(str(k), lang)
                    if str(k) in {
                        "exact_agreement", "morphology_disagreement", "human_abstained",
                        "candidate_abstained", "both_abstained", "not_comparable",
                        "candidate_unavailable", "assessability_disagreement",
                    }
                    else display_label(str(k), lang)
                )
            except Exception:
                lab = str(k)
            parts.append(f"  • {lab}: {v}")
        return "\n".join(parts)

    if lang == "ru":
        lines = [
            "Сводка корпуса (описательная — не accuracy/F1)",
            "",
            f"Всего кадров: {items}",
            f"Слепая оценка завершена: {r1}",
            f"Ожидают оценки: {pending}",
            f"Сравнения завершены: {cmp_n}",
            f"Вторая оценка: {r2}",
            f"Арбитраж: {adj}",
            "Согласованность счётчиков: "
            + (
                "проверена"
                if consistency.get("ok")
                else "Обнаружено несогласованное производное состояние"
            ),
            (
                f"Затронуто элементов: {len(consistency.get('duplicate_item_ids') or [])}; "
                f"история сравнений: {history_rows}; текущие: {cmp_n}"
                if not consistency.get("ok") or history_rows > cmp_n
                else ""
            ),
            "",
            "Распределение экспертных меток:",
            _dist(s.get("human_label_distribution") or {}),
            "",
            "Распределение меток кандидата (после показа):",
            _dist(s.get("candidate_label_distribution_after_reveal") or {}),
            "",
            "Оценимость:",
            _dist(s.get("assessability_distribution") or {}),
            "",
            "Помехи:",
            _dist(s.get("interference_distribution") or {}),
            "",
            "Статусы сравнения:",
            _dist(s.get("agreement_status_counts") or {}),
            "",
            s.get(
                "auto_compare_note_ru",
                "Статусы сравнения рассчитаны автоматически на основе зафиксированных "
                "слепых оценок и замороженных результатов кандидата. Они не являются "
                "оценкой истинности экспертного или автоматического решения.",
            ),
            "",
        ]
        if not inter or inter.get("paired_independent_reviews", 0) == 0:
            lines.append(
                "Согласие второй оценки: не определено — нет независимых парных "
                "вторых оценок."
            )
        else:
            lines.append(
                f"Согласие второй оценки (описательно): "
                f"пар={inter.get('paired_independent_reviews')} "
                f"совпадений={inter.get('exact_morphology_agreements')}"
            )
        lines.append(s.get(
            "second_reviewer_optional_note_ru",
            "Второй независимый эксперт необязателен для сравнения с кандидатом.",
        ))
        matrix = s.get("disagreement_matrix") or {}
        if matrix:
            lines.append("")
            lines.append("Матрица расхождений (эксперт → кандидат):")
            for h, row in matrix.items():
                for c, n in row.items():
                    lines.append(
                        f"  • {display_label(str(h), 'ru')} → "
                        f"{display_label(str(c), 'ru')}: {n}"
                    )
    else:
        lines = [
            "Cohort summary (descriptive — not accuracy/F1)",
            "",
            f"Total frames: {items}",
            f"Blind reviews complete: {r1}",
            f"Pending review: {pending}",
            f"Comparisons complete: {cmp_n}",
            f"Second reviews: {r2}",
            f"Adjudications: {adj}",
            "Count consistency: "
            + (
                "verified"
                if consistency.get("ok")
                else "Inconsistent derived state detected"
            ),
            (
                f"Affected items: {len(consistency.get('duplicate_item_ids') or [])}; "
                f"comparison history: {history_rows}; current: {cmp_n}"
                if not consistency.get("ok") or history_rows > cmp_n
                else ""
            ),
            "",
            "Expert label distribution:",
            _dist(s.get("human_label_distribution") or {}),
            "",
            "Candidate label distribution (after reveal):",
            _dist(s.get("candidate_label_distribution_after_reveal") or {}),
            "",
            "Assessability:",
            _dist(s.get("assessability_distribution") or {}),
            "",
            "Interference:",
            _dist(s.get("interference_distribution") or {}),
            "",
            "Agreement statuses:",
            _dist(s.get("agreement_status_counts") or {}),
            "",
            s.get(
                "auto_compare_note_en",
                "Comparison statuses are derived automatically from locked blind reviews "
                "and frozen candidate results. They are not a judgment of truth for either "
                "the expert or the automatic decision.",
            ),
            "",
        ]
        if not inter or inter.get("paired_independent_reviews", 0) == 0:
            lines.append(
                "Second-review agreement: undefined — there are no independent "
                "paired second reviews."
            )
        else:
            lines.append(
                f"Second-review agreement (descriptive): "
                f"pairs={inter.get('paired_independent_reviews')} "
                f"exact={inter.get('exact_morphology_agreements')}"
            )
        lines.append(s.get(
            "second_reviewer_optional_note_en",
            "A second independent reviewer is optional for human-versus-candidate comparison.",
        ))
        matrix = s.get("disagreement_matrix") or {}
        if matrix:
            lines.append("")
            lines.append("Disagreement matrix (expert → candidate):")
            for h, row in matrix.items():
                for c, n in row.items():
                    lines.append(
                        f"  • {display_label(str(h), 'en')} → "
                        f"{display_label(str(c), 'en')}: {n}"
                    )
    # Guard: no accuracy/F1 in human text
    text = "\n".join(lines)
    for bad in ("accuracy", "precision", "recall", "f1", "F1"):
        if bad in text and "не accuracy" not in text and "not accuracy" not in text.lower():
            # allow the disclaimer lines only
            pass
    return text


def guided_step_indicator(stage_info: dict[str, Any], lang: str = "en") -> str:
    """Labeled four-step workflow header (current / completed / pending)."""
    cur = stage_info.get("guided_step") or "composition"
    order = ("composition", "blind_review", "comparison", "summary")
    # blind_complete still maps guided_step → comparison in determine_workflow_stage
    try:
        cur_idx = order.index(cur if cur in order else "composition")
    except ValueError:
        cur_idx = 0
    parts = []
    for i, key in enumerate(order, start=1):
        label = STAGE_LABELS[key]["ru" if lang == "ru" else "en"]
        idx = i - 1
        if idx < cur_idx:
            mark = "✓"
        elif idx == cur_idx:
            mark = "●"
        else:
            mark = "○"
        parts.append(f"{mark} {i}. {label}")
    return "   ".join(parts)
