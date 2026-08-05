"""Review-corpus status model with RU/EN labels (no raw-ID fallback)."""

from __future__ import annotations

STATUS_LABELS: dict[str, dict[str, str]] = {
    "cohort_draft": {
        "en": "Cohort draft",
        "ru": "Черновик корпуса",
        "explain_en": "Cohort may still be edited before freeze.",
        "explain_ru": "Корпус ещё можно редактировать до фиксации.",
    },
    "cohort_frozen": {
        "en": "Cohort frozen",
        "ru": "Корпус зафиксирован",
        "explain_en": "Manifest, protocol, and sampling are immutable.",
        "explain_ru": "Манифест, протокол и выборка неизменяемы.",
    },
    "item_pending": {
        "en": "Pending review",
        "ru": "Ожидает оценки",
        "explain_en": "No locked blind review yet.",
        "explain_ru": "Слепая оценка ещё не зафиксирована.",
    },
    "item_unavailable": {
        "en": "Unavailable",
        "ru": "Недоступен",
        "explain_en": "Source/frame cannot be loaded; entry retained.",
        "explain_ru": "Источник/кадр недоступен; запись сохранена.",
    },
    "blind_review_in_progress": {
        "en": "Blind review in progress",
        "ru": "Слепая оценка в работе",
        "explain_en": "Reviewer is filling required axes; candidate hidden.",
        "explain_ru": "Заполняются оси оценки; кандидат скрыт.",
    },
    "blind_review_locked": {
        "en": "Blind review locked",
        "ru": "Слепая оценка зафиксирована",
        "explain_en": "Blind decision is append-only locked; reveal may proceed.",
        "explain_ru": "Слепое решение зафиксировано; можно показать кандидата.",
    },
    "second_review_pending": {
        "en": "Second review pending",
        "ru": "Ожидает второй оценки",
        "explain_en": "Independent second blind review not yet locked.",
        "explain_ru": "Независимая вторая слепая оценка ещё не зафиксирована.",
    },
    "second_review_locked": {
        "en": "Second review locked",
        "ru": "Вторая оценка зафиксирована",
        "explain_en": "Second independent blind review is locked.",
        "explain_ru": "Вторая независимая слепая оценка зафиксирована.",
    },
    "adjudication_pending": {
        "en": "Adjudication pending",
        "ru": "Ожидает арбитража",
        "explain_en": "Two reviews locked; adjudicator decision not yet locked.",
        "explain_ru": "Две оценки зафиксированы; арбитраж ещё не завершён.",
    },
    "adjudication_locked": {
        "en": "Adjudication locked",
        "ru": "Арбитраж зафиксирован",
        "explain_en": "Adjudicated expert reference recorded (not absolute ground truth).",
        "explain_ru": "Зафиксирован арбитражный экспертный ориентир (не абсолютная истина).",
    },
    "candidate_reveal_available": {
        "en": "Candidate reveal available",
        "ru": "Можно показать кандидата",
        "explain_en": "Blind lock complete; candidate may be revealed.",
        "explain_ru": "Слепая фиксация завершена; кандидата можно показать.",
    },
    "comparison_recorded": {
        "en": "Comparison recorded",
        "ru": "Сравнение записано",
        "explain_en": "Reveal comparison saved without altering the blind decision.",
        "explain_ru": "Сравнение сохранено без изменения слепой оценки.",
    },
    "item_complete": {
        "en": "Item complete",
        "ru": "Элемент завершён",
        "explain_en": "Required review workflow for this item is complete.",
        "explain_ru": "Требуемый рабочий процесс для элемента завершён.",
    },
    "review_superseded": {
        "en": "Review superseded",
        "ru": "Оценка замещена",
        "explain_en": "A newer append-only revision replaced this record as current.",
        "explain_ru": "Более новая ревизия заменила эту запись как текущую.",
    },
    "source_mismatch": {
        "en": "Source mismatch",
        "ru": "Несовпадение источника",
        "explain_en": "Source SHA or frame does not match the review identity.",
        "explain_ru": "SHA источника или индекс кадра не совпадают с идентичностью.",
    },
    "incompatible_v2": {
        "en": "Incompatible V2",
        "ru": "Несовместимый V2",
        "explain_en": "Compatible Feature Pipeline V2 result is not available.",
        "explain_ru": "Совместимый результат Feature Pipeline V2 недоступен.",
    },
}


def status_label(status_id: str, lang: str = "en") -> str:
    row = STATUS_LABELS.get(status_id)
    if not row:
        raise ValueError(f"Unknown review status ID: {status_id!r}")
    return row["ru" if lang == "ru" else "en"]


def status_explanation(status_id: str, lang: str = "en") -> str:
    row = STATUS_LABELS.get(status_id)
    if not row:
        raise ValueError(f"Unknown review status ID: {status_id!r}")
    return row["explain_ru" if lang == "ru" else "explain_en"]


ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "cohort_draft": frozenset(
        {"edit_items", "edit_protocol", "freeze", "export_draft", "archive"}
    ),
    "cohort_frozen": frozenset(
        {"open_queue", "start_blind", "export", "revise_cohort", "validate"}
    ),
    "item_pending": frozenset({"start_blind", "mark_unavailable"}),
    "blind_review_locked": frozenset({"reveal", "second_review", "revise_blind"}),
    "candidate_reveal_available": frozenset({"reveal", "compare"}),
    "comparison_recorded": frozenset({"export", "second_review", "adjudicate"}),
    "second_review_locked": frozenset({"adjudicate", "compare_agreement"}),
    "adjudication_locked": frozenset({"reveal", "export"}),
}


def allowed_actions(status_id: str) -> frozenset[str]:
    if status_id not in STATUS_LABELS:
        raise ValueError(f"Unknown review status ID: {status_id!r}")
    return ALLOWED_ACTIONS.get(status_id, frozenset())
