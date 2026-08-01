"""Provisional archive time mapping for instrument profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeMappingStatus:
    available: bool
    status: str  # provisional | unavailable | confirmed_not_claimed
    warning_en: str
    warning_ru: str


def mapping_status(time_mapping: str | None) -> TimeMappingStatus:
    if time_mapping == "matlab_index_minus_1_minute":
        return TimeMappingStatus(
            available=True,
            status="provisional",
            warning_en=(
                "Archive-time interpretation is consistent with project evidence "
                "but is not metrologically confirmed. Do not present as confirmed clock time."
            ),
            warning_ru=(
                "Интерпретация архивного времени согласуется с данными проекта, "
                "но не подтверждена метрологически. Не представлять как подтверждённое время."
            ),
        )
    return TimeMappingStatus(
        available=False,
        status="unavailable",
        warning_en="Time navigation is disabled because no time mapping is defined for this profile.",
        warning_ru="Навигация по времени отключена: для профиля не задано сопоставление времени.",
    )


def frame_to_minute(matlab_frame_id: int) -> int:
    """1-based archive frame ID → provisional minute-of-day (0..1439)."""
    return int(matlab_frame_id) - 1


def minute_to_frame(minute: int) -> int:
    return int(minute) + 1


def format_hhmm(minute: int) -> str:
    m = max(0, min(1439, int(minute)))
    return f"{m // 60:02d}:{m % 60:02d}"


def parse_hhmm(text: str) -> int | None:
    text = (text or "").strip()
    if not text or ":" not in text:
        return None
    try:
        hh_s, mm_s = text.split(":", 1)
        hh, mm = int(hh_s), int(mm_s)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return hh * 60 + mm
    except ValueError:
        return None


def frame_label(matlab_frame_id: int, time_mapping: str | None) -> str:
    if mapping_status(time_mapping).available:
        return f"f{matlab_frame_id:04d} ≈ {format_hhmm(frame_to_minute(matlab_frame_id))} (provisional)"
    return f"f{matlab_frame_id:04d}"
