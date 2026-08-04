"""Structured runtime status messages (message_key + args) for RU/EN reformatting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class StatusMessage:
    key: str
    args: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    generation: str = ""
    identity: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "args": dict(self.args),
            "severity": self.severity,
            "generation": self.generation,
            "identity": dict(self.identity),
        }


_TEMPLATES: dict[str, dict[str, str]] = {
    "v2_cache_loaded": {
        "ru": "Результат загружен из кэша V2.",
        "en": "Result loaded from V2 cache.",
    },
    "v2_recalculated": {
        "ru": "V2 пересчитан для кадра {frame}.",
        "en": "V2 recalculated for frame {frame}.",
    },
    "candidate_cache_loaded": {
        "ru": "Кандидат морфологии загружен из кэша.",
        "en": "Morphology candidate loaded from cache.",
    },
    "candidate_newly_evaluated": {
        "ru": "Кандидат морфологии рассчитан заново.",
        "en": "Morphology candidate newly evaluated.",
    },
    "cached_return_both": {
        "ru": "V2 загружен из кэша; кандидат загружен из кэша.\nРасчёт не выполнялся.",
        "en": "V2 loaded from cache; candidate loaded from cache.\nNo computation was performed.",
    },
    "cached_return_v2_only": {
        "ru": "V2 загружен из кэша; кандидат не рассчитан.",
        "en": "V2 loaded from cache; candidate not calculated.",
    },
    "frame_loaded_no_v2": {
        "ru": "Кадр загружен. V2 для этого кадра не рассчитан.",
        "en": "Frame loaded. V2 has not been computed for this frame.",
    },
    "frame_loaded_candidate_cached": {
        "ru": "Кадр загружен. Кандидат морфологии загружен из кэша. Расчёт не выполнялся.",
        "en": "Frame loaded. Morphology candidate loaded from cache. No computation was performed.",
    },
    "frame_changed_cleared": {
        "ru": "Смена кадра: старые маски и кандидат очищены.",
        "en": "Frame changed: previous overlays and candidate cleared.",
    },
    "loading_frame": {
        "ru": "Загрузка кадра {frame}…",
        "en": "Loading frame {frame}…",
    },
    "sequence_count": {
        "ru": "Последовательность: {count} кадров.",
        "en": "Sequence: {count} frames.",
    },
    "source_ready": {
        "ru": "Источник готов.",
        "en": "Source ready.",
    },
    "display_ready": {
        "ru": "Отображение готово.",
        "en": "Display ready.",
    },
    "legacy_v2_incomplete": {
        "ru": "Неполный устаревший кэш V2. Требуется пересчёт V2.",
        "en": "Incomplete legacy V2 cache. V2 recalculation required.",
    },
    "incompatible_candidate_cache": {
        "ru": "Кэш кандидата создан предыдущей версией. Пересчитайте только кандидата; пересчёт V2 не требуется.",
        "en": "Candidate cache was created by a previous version. Recalculate the candidate only; V2 recalculation is not required.",
    },
    "cancel_requested": {
        "ru": "Отмена запрошена.",
        "en": "Cancel requested.",
    },
    "cancelled": {
        "ru": "Отменено.",
        "en": "Cancelled.",
    },
    "evidence_json_copied": {
        "ru": "JSON доказательств скопирован.",
        "en": "Evidence JSON copied.",
    },
    "identity_mismatch_review": {
        "ru": "Идентичность кандидата изменилась. Сохранение проверки заблокировано.",
        "en": "Candidate identity changed. Review save is blocked.",
    },
    "no_candidate": {
        "ru": "Нет кандидата.",
        "en": "No candidate.",
    },
}


def format_status(msg: StatusMessage | Mapping[str, Any] | None, lang: str) -> str:
    if msg is None:
        return ""
    if isinstance(msg, StatusMessage):
        key = msg.key
        args = msg.args
    else:
        key = str(msg.get("key") or "")
        args = dict(msg.get("args") or {})
    tmpl = (_TEMPLATES.get(key) or {}).get(lang) or (_TEMPLATES.get(key) or {}).get("en") or key
    try:
        return tmpl.format(**args)
    except (KeyError, ValueError):
        return tmpl


# Cyrillic block — used by mixed-language validator for EN mode
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def contains_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC_RE.search(text or ""))


def assert_status_language(text: str, lang: str) -> list[str]:
    """Return validation errors if visible status mixes languages incorrectly."""
    errors: list[str] = []
    if not text:
        return errors
    if lang == "en" and contains_cyrillic(text):
        errors.append(f"EN status contains Cyrillic: {text[:80]!r}")
    return errors
