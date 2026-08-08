"""Bilingual display helpers for ML-C.1 — canonical IDs stay internal."""
from __future__ import annotations

from typing import Any

from .constants import BASELINE_LOGISTIC, BASELINE_MAJORITY, BASELINE_NEAREST_CENTROID

_BASELINES = {
    BASELINE_MAJORITY: {"en": "Majority Class", "ru": "Класс большинства"},
    BASELINE_NEAREST_CENTROID: {"en": "Nearest Centroid", "ru": "Ближайший центроид"},
    BASELINE_LOGISTIC: {"en": "Logistic Regression", "ru": "Логистическая регрессия"},
}
_STATES = {
    "draft": {"en": "Draft", "ru": "Черновик"},
    "validated": {"en": "Validated", "ru": "Проверен"},
    "running": {"en": "Running", "ru": "Выполняется"},
    "completed": {"en": "Completed", "ru": "Завершён"},
    "failed": {"en": "Failed", "ru": "Ошибка"},
    "cancelled": {"en": "Cancelled", "ru": "Отменён"},
    "archived": {"en": "Archived", "ru": "Архивирован"},
}

_MISSING = "—"


def baseline_label(version: str, lang: str = "en") -> str:
    code = "ru" if str(lang).startswith("ru") else "en"
    return _BASELINES.get(version, {}).get(code, version)


def state_label(state: str, lang: str = "en") -> str:
    code = "ru" if str(lang).startswith("ru") else "en"
    return _STATES.get(state, {}).get(code, state)


def metrics_scope_label(lang: str = "en") -> str:
    if str(lang).startswith("ru"):
        return "Метрики только development — не независимая валидация."
    return "Development metrics only — not independent validation."


def sealed_short(lang: str = "en") -> str:
    return "ЗАПЕЧАТАН" if str(lang).startswith("ru") else "SEALED"


def format_metric_value(value: Any, lang: str = "en") -> str:
    """Render metric values for normal UI. Never show Python None; never coerce null→0.0."""
    if value is None:
        return "Не определено" if str(lang).startswith("ru") else "N/A"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if float(value) == 0.0:
            return "0.0"
        return f"{float(value):.6g}"
    text = str(value)
    if text in {"None", "null"}:
        return "Не определено" if str(lang).startswith("ru") else "N/A"
    return text


def format_optional_cell(value: Any) -> str:
    if value is None:
        return _MISSING
    text = str(value).strip()
    return text if text else _MISSING


def morphology_display_name(canonical: str, lang: str = "en") -> str:
    """Human-readable morphology name when i18n helpers exist; else canonical token."""
    try:
        from ionogram_morphology_lab.morphology_review_corpus.labels import morphology_label

        return morphology_label(canonical, lang)
    except Exception:
        return str(canonical)
