"""Acquisition-date authority and validation for ML readiness inventories.

Root cause (ML-A.1a.1): inventory resolved ``source_date`` from
``grouping["source_date"]`` (often absent) and then fell back to
``frame_time`` / ``frame_time[:10]``. Real pilot frames use HH:MM times
(e.g. ``04:59``), so each frame became a false unique “date”. Corpus
items typically store the acquisition hint as ``grouping["date"]`` /
``datetime_metadata`` / filename ``Am_all_2014-10-15.mat``.
"""

from __future__ import annotations

import re
from typing import Any

_ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T\s].*)?$")
_FILENAME_DATE_RE = re.compile(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})")
# Bare clock times — never acquisition dates
_TIME_ONLY_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:\s*[AaPp][Mm])?$"
)


def is_time_only_value(value: str) -> bool:
    s = str(value or "").strip()
    if not s:
        return False
    return bool(_TIME_ONLY_RE.match(s))


def is_valid_acquisition_date(value: str) -> bool:
    """True only for canonical YYYY-MM-DD (not times, not filenames)."""
    s = str(value or "").strip()
    if not s or is_time_only_value(s):
        return False
    m = _ISO_DATE_RE.match(s)
    if not m:
        return False
    # Reject nonsense months/days lightly
    try:
        y, mo, d = (int(x) for x in m.group(1).split("-"))
        return 1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31
    except ValueError:
        return False


def normalize_acquisition_date(*candidates: str) -> str:
    """Return first valid YYYY-MM-DD from candidates. Never accepts time-only."""
    for cand in candidates:
        s = str(cand or "").strip()
        if not s or is_time_only_value(s):
            continue
        m = _ISO_DATE_RE.match(s)
        if m and is_valid_acquisition_date(m.group(1)):
            return m.group(1)
    return ""


def parse_date_from_filename(name: str) -> str:
    """Deterministic date from recognized source filename patterns."""
    s = str(name or "").strip()
    if not s:
        return ""
    # Use basename only — never absolute paths
    base = s.replace("\\", "/").rsplit("/", 1)[-1]
    m = _FILENAME_DATE_RE.search(base)
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def resolve_acquisition_date(
    *,
    source_inventory_date: str = "",
    cohort_manifest_date: str = "",
    grouping: dict[str, Any] | None = None,
    datetime_metadata: str = "",
    source_display_name: str = "",
    mat_metadata_date: str = "",
) -> str:
    """Resolve acquisition date by documented authority order.

    Never uses frame time, frame index, review timestamp, or mtime.
    """
    g = grouping or {}
    # 1) authoritative project source-inventory acquisition date
    # 2) validated cohort/source manifest / grouping date keys
    # 3) validated MAT/source metadata date (datetime_metadata when date-like)
    # 4) deterministic filename parse
    # 5) missing
    return normalize_acquisition_date(
        source_inventory_date,
        cohort_manifest_date,
        str(g.get("source_date") or ""),
        str(g.get("acquisition_date") or ""),
        str(g.get("date") or ""),
        mat_metadata_date,
        datetime_metadata,
        parse_date_from_filename(source_display_name),
    )


def diagnose_invalid_date_projection(rows: list[Any]) -> dict[str, Any]:
    """Detect legacy inventories where acquisition_date holds time-only values."""
    invalid_time_as_date = 0
    valid_dates: set[str] = set()
    invalid_values: set[str] = set()
    missing = 0
    for r in rows:
        sd = str(getattr(r, "source_date", "") or "")
        if not sd:
            missing += 1
            continue
        if is_time_only_value(sd) or not is_valid_acquisition_date(sd):
            invalid_time_as_date += 1
            invalid_values.add(sd)
        else:
            valid_dates.add(sd)
    frame_times = {
        str(getattr(r, "frame_time", "") or "")
        for r in rows
        if str(getattr(r, "frame_time", "") or "").strip()
    }
    # Heuristic: many distinct time-like "dates" equal frame times → legacy bug
    legacy_like = invalid_time_as_date > 0 and (
        invalid_time_as_date >= max(1, len(rows) // 2)
        or (len(invalid_values) > 1 and invalid_values <= frame_times)
    )
    return {
        "has_invalid_acquisition_dates": invalid_time_as_date > 0,
        "legacy_invalid_date_projection": legacy_like,
        "invalid_time_as_date_count": invalid_time_as_date,
        "invalid_values": sorted(invalid_values),
        "valid_unique_source_dates": len(valid_dates),
        "missing_source_date_count": missing,
        "unique_frame_times": len(frame_times),
        "warning_en": (
            "This audit was created by an older version with an invalid acquisition "
            "date projection. Create a corrected audit revision."
            if legacy_like
            else ""
        ),
        "warning_ru": (
            "Этот аудит создан старой версией с некорректной проекцией даты. "
            "Создайте исправленную ревизию аудита."
            if legacy_like
            else ""
        ),
    }


LEGACY_DATE_WARNING_EN = (
    "This audit was created by an older version with an invalid acquisition "
    "date projection. Create a corrected audit revision."
)
LEGACY_DATE_WARNING_RU = (
    "Этот аудит создан старой версией с некорректной проекцией даты. "
    "Создайте исправленную ревизию аудита."
)

MISSING_DATE_LABEL = {
    "en": "Date not determined",
    "ru": "Дата не определена",
}
