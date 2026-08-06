"""Localized display labels for ML readiness UI (canonical codes stay in exports)."""

from __future__ import annotations

from ionogram_morphology_lab.ml_dataset_readiness.contracts import CONTRACT_LABELS
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import GATE_LABELS
from ionogram_morphology_lab.morphology_review_corpus.labels import display_label

_DENOM: dict[str, dict[str, str]] = {
    "selected_records": {"en": "Selected records", "ru": "Выбрано записей"},
    "unique_current_items": {
        "en": "Unique current items",
        "ru": "Уникальных текущих элементов",
    },
    "raw_frame_count": {"en": "Raw frame count", "ru": "Число кадров (сырое)"},
    "unique_related_frame_groups": {
        "en": "Unique related-frame groups",
        "ru": "Уникальных групп связанных кадров",
    },
    "unique_sequences": {"en": "Unique sequences", "ru": "Уникальных последовательностей"},
    "unique_source_dates": {
        "en": "Unique source / acquisition dates",
        "ru": "Уникальных дат источника / съёмки",
    },
    "unique_frame_times": {
        "en": "Unique frame times",
        "ru": "Уникальных времён кадров",
    },
    "unique_sources": {"en": "Unique sources", "ru": "Уникальных источников"},
    "unique_campaigns": {"en": "Unique campaigns", "ru": "Уникальных кампаний"},
    "locked_first_reviews": {
        "en": "Locked first reviews",
        "ru": "Зафиксированных первых оценок",
    },
    "independent_second_reviews": {
        "en": "Independent second reviews",
        "ru": "Независимых вторых оценок",
    },
    "items_with_paired_independent_reviews": {
        "en": "Items with paired independent reviews",
        "ru": "Элементов с парными независимыми оценками",
    },
    "arbitration_records": {"en": "Arbitration records", "ru": "Записей арбитража"},
    "corrected_first_reviews": {
        "en": "Corrected first reviews",
        "ru": "Исправленных первых оценок",
    },
    "corrected_second_reviews": {
        "en": "Corrected second reviews",
        "ru": "Исправленных вторых оценок",
    },
    "assessable": {"en": "Assessable", "ru": "Оценимо"},
    "partially_assessable": {"en": "Partially assessable", "ru": "Частично оценимо"},
    "not_assessable": {"en": "Not assessable", "ru": "Не поддаётся оценке"},
    "indeterminate_labels": {
        "en": "Indeterminate labels",
        "ru": "Неопределённых меток",
    },
    "abstentions": {"en": "Abstentions", "ru": "Воздержания"},
    "missing_required_fields": {
        "en": "Missing required fields",
        "ru": "Отсутствуют обязательные поля",
    },
    "unavailable_sources": {"en": "Unavailable sources", "ru": "Недоступные источники"},
    "development_exposed_items": {
        "en": "Development-exposed items",
        "ru": "Элементов, использованных в разработке",
    },
    "untouched_eligible_items": {
        "en": "Untouched-holdout-eligible items",
        "ru": "Элементов, допустимых для независимого holdout",
    },
    "synthetic_related_frame_groups": {
        "en": "Synthetic related-frame group identities",
        "ru": "Синтетических идентификаторов групп кадров",
    },
}

_MISS: dict[str, dict[str, str]] = {
    "structurally_missing": {"en": "Structurally missing", "ru": "Структурно отсутствует"},
    "not_applicable": {"en": "Not applicable", "ru": "Не применимо"},
    "expert_abstained": {"en": "Expert abstained", "ru": "Эксперт воздержался"},
    "unavailable_data": {"en": "Unavailable data", "ru": "Данные недоступны"},
    "corrupted_identity": {"en": "Corrupted identity", "ru": "Повреждённая идентичность"},
}

_LIFE: dict[str, dict[str, str]] = {
    "draft": {"en": "Draft", "ru": "Черновик"},
    "frozen": {"en": "Frozen", "ru": "Заморожен"},
    "reviewed": {"en": "Reviewed", "ru": "Просмотрен"},
    "gate_recorded": {"en": "Gate recorded", "ru": "Решение зафиксировано"},
    "archived": {"en": "Archived", "ru": "Архив"},
}

_REVIEW: dict[str, dict[str, str]] = {
    "first_review_count": {"en": "First reviews", "ru": "Первые оценки"},
    "independent_second_review_count": {
        "en": "Independent second reviews",
        "ru": "Независимые вторые оценки",
    },
    "items_with_paired_independent_reviews": {
        "en": "Paired independent reviews",
        "ru": "Парные независимые оценки",
    },
    "arbitration_count": {"en": "Arbitration", "ru": "Арбитраж"},
    "corrected_first_reviews": {
        "en": "Corrected first reviews",
        "ru": "Исправленные первые оценки",
    },
    "corrected_second_reviews": {
        "en": "Corrected second reviews",
        "ru": "Исправленные вторые оценки",
    },
    "classes_one_expert_only": {
        "en": "Classes with one expert only",
        "ru": "Классы только с одним экспертом",
    },
    "classes_multiple_independent_experts": {
        "en": "Classes with multiple independent experts",
        "ru": "Классы с несколькими независимыми экспертами",
    },
    "classes_with_arbitration": {
        "en": "Classes with arbitration",
        "ru": "Классы с арбитражем",
    },
}

REVIEW_NOTE = {
    "en": (
        "A corrected review from the same expert is not an independent second opinion. "
        "The candidate result is also not a reviewer and not an expert review."
    ),
    "ru": (
        "Исправленная оценка того же эксперта не является независимым вторым "
        "мнением. Результат кандидата также не является экспертной оценкой."
    ),
}

SEQUENCE_CORRELATION_NOTE = {
    "en": (
        "Frames that share one sequence are correlated observations from the same "
        "physical event context and are not fully independent."
    ),
    "ru": (
        "Кадры одной последовательности — коррелированные наблюдения одного "
        "физического контекста и не являются полностью независимыми."
    ),
}

SYNTHETIC_GROUP_NOTE = {
    "en": (
        "Related-frame group identity is missing or synthetic for some rows; "
        "do not treat the synthetic group count as evidence of independence. "
        "Prefer sequence identity for holdout grouping interpretation."
    ),
    "ru": (
        "Идентичность группы связанных кадров отсутствует или синтетическая; "
        "не считайте синтетический счётчик доказательством независимости. "
        "Для интерпретации holdout опирайтесь на идентичность последовательности."
    ),
}


def _pick(table: dict[str, dict[str, str]], key: str, lang: str) -> str:
    row = table.get(key) or {}
    return row.get(lang) or row.get("en") or key


def denom_label(key: str, lang: str = "en") -> str:
    return _pick(_DENOM, key, lang)


def missingness_label(key: str, lang: str = "en") -> str:
    return _pick(_MISS, key, lang)


def lifecycle_label(key: str, lang: str = "en") -> str:
    return _pick(_LIFE, key, lang)


def review_field_label(key: str, lang: str = "en") -> str:
    return _pick(_REVIEW, key, lang)


def contract_label(contract_id: str, lang: str = "en") -> str:
    row = CONTRACT_LABELS.get(contract_id) or {}
    return row.get(lang) or row.get("en") or contract_id


def gate_outcome_label(code: str, lang: str = "en") -> str:
    row = GATE_LABELS.get(code) or {}
    return row.get(lang) or row.get("en") or code


def class_label(code: str, lang: str = "en") -> str:
    if not code or code == "(empty)":
        return "—" if lang != "ru" else "—"
    return display_label(code, lang)


# Known raw codes that must not appear in normal RU UI text dumps
# Field/lifecycle/gate codes that must not appear as bare keys in normal RU UI.
RAW_CODES_FORBIDDEN_IN_RU_UI = frozenset(
    {
        "selected_records",
        "unique_current_items",
        "development_exposed_items",
        "untouched_eligible_items",
        "expert_abstained",
        "structurally_missing",
        "gate_recorded",
        "A_collect_more_expert_labels",
        "C_expand_class_source_date_sequence_coverage",
        "authorizes_training",
        "note_en",
        "assessment_kind",
        "appears_possible",
        "not_applicable",
        "unavailable_data",
        "corrupted_identity",
    }
)
