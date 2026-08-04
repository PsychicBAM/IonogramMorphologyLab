"""RU/EN labels for provisional morphology candidates."""

from __future__ import annotations

CANDIDATE_LABELS = {
    "frequency_spread_candidate": {
        "ru": "Кандидат частотного рассеяния",
        "en": "Frequency-spread candidate",
    },
    "range_spread_candidate": {
        "ru": "Кандидат высотного рассеяния",
        "en": "Range-spread candidate",
    },
    "mixed_spread_candidate": {
        "ru": "Кандидат смешанного рассеяния",
        "en": "Mixed-spread candidate",
    },
    "no_supported_visible_spread": {
        "ru": "Поддерживаемое видимое рассеяние не обнаружено",
        "en": "No supported visible spread detected",
    },
    "indeterminate": {
        "ru": "Неопределённо",
        "en": "Indeterminate",
    },
    "not_assessable": {
        "ru": "Оценка невозможна",
        "en": "Not assessable",
    },
}

STRENGTH_LABELS = {
    "none": {"ru": "нет", "en": "none"},
    "weak": {"ru": "слабая", "en": "weak"},
    "moderate": {"ru": "умеренная", "en": "moderate"},
    "strong": {"ru": "сильная", "en": "strong"},
}

SHADOW_DISCLAIMER = {
    "ru": (
        "Предварительный кандидат в теневом режиме. Не является подтверждённой "
        "экспертной классификацией."
    ),
    "en": (
        "Provisional shadow-mode candidate. Not a confirmed expert classification."
    ),
}


def candidate_label(candidate: str, lang: str) -> str:
    entry = CANDIDATE_LABELS.get(candidate, {})
    return entry.get(lang, candidate)


def strength_label(strength: str, lang: str) -> str:
    return STRENGTH_LABELS.get(strength, {}).get(lang, strength)


def disclaimer(lang: str) -> str:
    return SHADOW_DISCLAIMER.get(lang, SHADOW_DISCLAIMER["en"])
