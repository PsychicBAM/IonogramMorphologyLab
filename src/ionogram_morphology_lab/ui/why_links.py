"""“Why?” explanations for non-obvious scientific/UI states."""

from __future__ import annotations

WHY: dict[str, dict[str, str]] = {
    "provisional_profile": {
        "en": "The KFU profile is provisional: matrix shape and ff are supported by project evidence, "
        "but absolute MHz/km metrology and clock confirmation remain open. Height is nominal virtual height.",
        "ru": "Профиль KFU провизорный: форма матрицы и ff подтверждены материалами проекта, "
        "но абсолютная метрология МГц/км и часы остаются открытыми. Высота — номинальная виртуальная.",
    },
    "nominal_virtual_height": {
        "en": "The vertical axis is nominal virtual height from the instrument profile mapping, "
        "not inverted true height. Do not treat bin indices as calibrated kilometers without verification.",
        "ru": "Вертикальная ось — номинальная виртуальная высота из профиля, не истинная высота. "
        "Не считайте бины калиброванными километрами без проверки.",
    },
    "uncalibrated_confidence": {
        "en": "Numerical confidence is shown only when the active model has adequate calibration. "
        "Otherwise the application displays a qualitative status and explains why a percentage is unavailable.",
        "ru": "Числовая уверенность показывается только при адекватной калибровке активной модели. "
        "Иначе отображается качественный статус и пояснение, почему процент недоступен.",
    },
    "abstention": {
        "en": "Abstention means evidence is insufficient or contradictory for a proposal on this axis. "
        "It is a valid scientific outcome, not a crash.",
        "ru": "Воздержание означает, что данных недостаточно или они противоречивы для предложения на этой оси. "
        "Это допустимый научный исход, а не сбой.",
    },
    "source_disabled_rule": {
        "en": "The rule is inactive because its verification status or threshold origin is not allowed "
        "in the current analysis mode (e.g. Scientific Strict).",
        "ru": "Правило неактивно: статус проверки или происхождение порога не допускаются "
        "в текущем режиме анализа (например Scientific Strict).",
    },
    "method_disagreement": {
        "en": "Methods disagree when candidate outputs differ under documented inputs. "
        "Agreement does not validate a method; disagreement remains visible for expert review.",
        "ru": "Методы расходятся, когда кандидатные выходы отличаются при документированных входах. "
        "Согласие не валидирует метод; разногласие остаётся видимым для эксперта.",
    },
    "missing_matlab_backend": {
        "en": "No MATLAB/Octave executable was detected. Core analysis still works; "
        "MATLAB Studio teaching runs require configuring a backend in Settings.",
        "ru": "Исполняемый файл MATLAB/Octave не обнаружен. Базовый анализ работает; "
        "для MATLAB Studio настройте бэкенд в Настройках.",
    },
    "metadata_only_reference": {
        "en": "This reference is metadata-only (e.g. copyrighted figure not redistributed). "
        "Citations remain; pixel data may be unavailable.",
        "ru": "Ссылка только с метаданными (например, защищённый копирайтом рисунок не распространяется). "
        "Цитирование сохраняется; пиксельные данные могут быть недоступны.",
    },
    "unavailable_parameter": {
        "en": "The parameter is unavailable because required calibration, polarization, or profile "
        "metrology is missing. The application refuses to invent a value.",
        "ru": "Параметр недоступен: нет нужной калибровки, поляризации или метрологии профиля. "
        "Приложение не выдумывает значение.",
    },
}


def why_text(key: str, lang: str = "en") -> str:
    block = WHY.get(key, {})
    return block.get("ru" if lang == "ru" else "en", key)
