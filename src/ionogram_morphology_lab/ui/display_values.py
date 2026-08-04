"""Localized display values for normal UI — keep canonical tokens for exports/tech."""

from __future__ import annotations

DISPLAY = {
    "en": {
        "valid": "Fit for analysis",
        "valid_with_warning": "Fit for analysis (with warning)",
        "degraded": "Degraded",
        "indeterminate": "Indeterminate",
        "uncertain": "Uncertain result",
        "uncalibrated": "Numerical confidence not calibrated",
        "no_visible_ambiguity": "No visible ambiguity",
        "no": "No",
        "yes": "Yes",
        "pending": "Pending expert review",
        "proposed": "Proposed",
        "accepted": "Accepted",
        "profile_dependent": "Depends on instrument profile",
        "source_disabled": "Disabled — unconfirmed source",
        "unavailable": "Unavailable",
        "provisional": "Provisional",
        "none": "None",
        "scientific_strict": "Scientific strict",
        "standard": "Standard analysis",
        "fast_preview": "Quick preview",
        "custom": "Custom",
        "raw": "Raw",
        "auto": "Automatic",
        "full": "Full",
        "fast": "Fast",
        "low": "Low",
        "present": "Present",
        "significant": "Significant",
        "dominant": "Dominant",
        "prevents_assessment": "Prevents assessment",
    },
    "ru": {
        "valid": "Пригоден для анализа",
        "valid_with_warning": "Пригоден с предупреждением",
        "degraded": "Ухудшенное качество",
        "indeterminate": "Не определён",
        "uncertain": "Неуверенный результат",
        "uncalibrated": "Численная уверенность не откалибрована",
        "no_visible_ambiguity": "Явная неоднозначность не обнаружена",
        "no": "Нет",
        "yes": "Да",
        "pending": "Ожидает проверки эксперта",
        "proposed": "Предложено",
        "accepted": "Принято",
        "profile_dependent": "Зависит от профиля прибора",
        "source_disabled": "Отключено из-за отсутствия подтверждённого источника",
        "unavailable": "Недоступно",
        "provisional": "Предварительный",
        "none": "Нет",
        "scientific_strict": "Научно строгий",
        "standard": "Стандартный анализ",
        "fast_preview": "Быстрый просмотр",
        "custom": "Настраиваемый",
        "raw": "Исходный",
        "auto": "Автоматически",
        "full": "Полный",
        "fast": "Быстрый",
        "low": "Низкий уровень",
        "present": "Присутствуют",
        "significant": "Значительные",
        "dominant": "Доминируют",
        "prevents_assessment": "Исключают оценку",
    },
}


def display_status(token: str | None, lang: str = "en") -> str:
    if token is None or token == "":
        return "—"
    key = str(token).strip()
    table = DISPLAY.get(lang, DISPLAY["en"])
    if key in table:
        return table[key]
    low = key.lower()
    if low in table:
        return table[low]
    return key
