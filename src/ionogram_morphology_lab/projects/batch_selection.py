"""User-friendly batch frame selection with expected-count explanations."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from ionogram_morphology_lab.projects.time_mapping import (
    format_hhmm,
    frame_to_minute,
    minute_to_frame,
    parse_hhmm,
)


@dataclass
class BatchSelection:
    mode: str
    frame_ids: list[int]
    explanation_en: str
    explanation_ru: str
    frame_interval: int | None = None
    time_interval_minutes: int | None = None
    operations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def expected_count(self) -> int:
        return len(self.frame_ids)


DEFAULT_KFU_INTERVAL_MINUTES = 10

ALL_OPERATIONS = [
    "audit",
    "build_cache",
    "render",
    "quality",
    "features",
    "rules",
    "references",
    "contact_sheet",
    "export_reports",
    "full_pipeline",
]


def _clamp_frames(ids: list[int], n_frames: int) -> list[int]:
    out = sorted({i for i in ids if 1 <= i <= n_frames})
    return out


def select_single(frame_id: int, n_frames: int = 1440) -> BatchSelection:
    ids = _clamp_frames([frame_id], n_frames)
    return BatchSelection(
        mode="single",
        frame_ids=ids,
        explanation_en=f"1 frame selected: frame {frame_id}.",
        explanation_ru=f"Выбран 1 кадр: кадр {frame_id}.",
        frame_interval=None,
        time_interval_minutes=None,
    )


def select_frame_range(
    start: int, end: int, step: int, n_frames: int = 1440
) -> BatchSelection:
    step = max(1, int(step))
    start, end = int(start), int(end)
    if end < start:
        start, end = end, start
    ids = _clamp_frames(list(range(start, end + 1, step)), n_frames)
    return BatchSelection(
        mode="frame_range",
        frame_ids=ids,
        frame_interval=step,
        time_interval_minutes=step if step else None,
        explanation_en=(
            f"{len(ids)} frames are selected because the interval is {step} frames "
            f"(from {start} to {end})."
        ),
        explanation_ru=(
            f"Выбрано {len(ids)} кадров, потому что используется шаг {step} кадр "
            f"(с {start} по {end})."
        ),
    )


def select_time_range(
    start_hhmm: str,
    end_hhmm: str,
    interval_minutes: int,
    n_frames: int = 1440,
) -> BatchSelection:
    s = parse_hhmm(start_hhmm)
    e = parse_hhmm(end_hhmm)
    if s is None or e is None:
        raise ValueError("invalid_time")
    interval = max(1, int(interval_minutes))
    if e < s:
        s, e = e, s
    minutes = list(range(s, e + 1, interval))
    ids = _clamp_frames([minute_to_frame(m) for m in minutes], n_frames)
    return BatchSelection(
        mode="time_range",
        frame_ids=ids,
        frame_interval=interval,
        time_interval_minutes=interval,
        explanation_en=(
            f"{len(ids)} frames are selected: {format_hhmm(s)}–{format_hhmm(e)}, "
            f"{interval}-minute step."
        ),
        explanation_ru=(
            f"Выбрано {len(ids)} кадров: {format_hhmm(s)}–{format_hhmm(e)}, "
            f"шаг {interval} минут."
        ),
    )


def select_full_day(interval_minutes: int, n_frames: int = 1440) -> BatchSelection:
    interval = max(1, int(interval_minutes))
    ids = _clamp_frames(list(range(1, n_frames + 1, interval)), n_frames)
    return BatchSelection(
        mode="full_day",
        frame_ids=ids,
        frame_interval=interval,
        time_interval_minutes=interval,
        explanation_en=(
            f"{len(ids)} frames are selected for a full day with a {interval}-minute "
            f"(≈{interval}-frame) interval."
        ),
        explanation_ru=(
            f"Выбрано {len(ids)} кадров за сутки с интервалом {interval} минут "
            f"(≈{interval} кадров)."
        ),
    )


def select_custom_list(items: list[str], n_frames: int = 1440) -> BatchSelection:
    ids: list[int] = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            m = parse_hhmm(item)
            if m is not None:
                ids.append(minute_to_frame(m))
        else:
            ids.append(int(item))
    ids = _clamp_frames(ids, n_frames)
    return BatchSelection(
        mode="custom_list",
        frame_ids=ids,
        explanation_en=f"{len(ids)} frames selected from a custom list.",
        explanation_ru=f"Выбрано {len(ids)} кадров из пользовательского списка.",
    )


def select_contact_sequence(
    center: int,
    rows: int,
    cols: int,
    step_minutes: int,
    n_frames: int = 1440,
) -> BatchSelection:
    count = rows * cols
    step = max(1, int(step_minutes))
    half = (count - 1) // 2
    start = center - half * step
    ids = [center + (i - half) * step for i in range(count)]
    ids = _clamp_frames(ids, n_frames)
    # if clamping removed some, rebuild from start
    if len(ids) < count:
        ids = _clamp_frames(list(range(max(1, start), n_frames + 1, step))[:count], n_frames)
    t0 = format_hhmm(frame_to_minute(ids[0])) if ids else "?"
    t1 = format_hhmm(frame_to_minute(ids[-1])) if ids else "?"
    return BatchSelection(
        mode="contact_sheet",
        frame_ids=ids,
        frame_interval=step,
        time_interval_minutes=step,
        explanation_en=(
            f"{len(ids)} ionograms will be generated: {t0}–{t1}, {step}-minute step "
            f"({rows}×{cols})."
        ),
        explanation_ru=(
            f"Будет создано {len(ids)} ионограмм: {t0}–{t1}, шаг {step} минут "
            f"({rows}×{cols})."
        ),
    )


def estimate_resources(selection: BatchSelection, bytes_per_frame: int = 256 * 400 * 8) -> dict[str, Any]:
    n = selection.expected_count
    mem = n * bytes_per_frame
    # rough heuristics
    render_s = n * 0.35
    analysis_s = n * 0.8
    return {
        "expected_frames": n,
        "estimated_memory_bytes": mem,
        "estimated_memory_mb": round(mem / (1024 * 1024), 1),
        "estimated_cache_mb": round((1440 * bytes_per_frame) / (1024 * 1024), 1),
        "estimated_render_seconds": round(render_s, 1),
        "estimated_analysis_seconds": round(analysis_s, 1),
    }
