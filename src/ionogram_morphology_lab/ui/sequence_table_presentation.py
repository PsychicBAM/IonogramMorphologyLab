"""Sequence Results table presentation — compact/full profiles and theme-safe markers.

UI-only. Does not alter V2 / candidate scientific payloads.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QFontMetrics

from ionogram_morphology_lab.ui.theme import ThemeName, resolve_theme_name, source_card_tokens

# Column indices match FeatureDiagnosticsPage._sequence_row_values order.
SEQ_COL_FRAME = 0
SEQ_COL_TIME = 1
SEQ_COL_QUALITY = 2
SEQ_COL_TRACE = 3
SEQ_COL_BRANCHES = 4
SEQ_COL_INTERF = 5
SEQ_COL_H = 6
SEQ_COL_V = 7
SEQ_COL_ASSESS = 8
SEQ_COL_CANDIDATE = 9
SEQ_COL_STRENGTH = 10
SEQ_COL_HSUP = 11
SEQ_COL_VSUP = 12
SEQ_COL_INTERFL = 13
SEQ_COL_TEMPORAL = 14
SEQ_COL_ABSTENTION = 15
SEQ_COL_CACHE = 16
SEQ_COL_MORPH_REV = 17
SEQ_COL_GEOM_REV = 18

SEQ_COLUMN_COUNT = 19

# Compact embedded profile — high-value navigation columns.
COMPACT_VISIBLE_COLUMNS: tuple[int, ...] = (
    SEQ_COL_FRAME,
    SEQ_COL_TIME,
    SEQ_COL_QUALITY,
    SEQ_COL_TRACE,
    SEQ_COL_BRANCHES,
    SEQ_COL_INTERF,
    SEQ_COL_H,
    SEQ_COL_V,
    SEQ_COL_ASSESS,
    SEQ_COL_CANDIDATE,
    SEQ_COL_STRENGTH,
)

FULL_VISIBLE_COLUMNS: tuple[int, ...] = tuple(range(SEQ_COLUMN_COUNT))

# Essential columns that Reset / Compact always restore.
ESSENTIAL_COLUMNS: frozenset[int] = frozenset({SEQ_COL_FRAME, SEQ_COL_TIME})

COLUMN_KEYS: tuple[str, ...] = (
    "frame",
    "time",
    "quality",
    "trace",
    "branches",
    "interf",
    "H",
    "V",
    "assess",
    "candidate",
    "strength",
    "Hsup",
    "Vsup",
    "interfL",
    "temporal",
    "abstention",
    "cache",
    "morph_rev",
    "geom_rev",
)


@dataclass(frozen=True)
class SeqRowMarkerColors:
    background: QColor
    foreground: QColor


def sequence_header_labels(language: str) -> list[str]:
    ru = language == "ru"
    if ru:
        return [
            "кадр",
            "время",
            "качество",
            "след",
            "ветви",
            "помехи",
            "H",
            "V",
            "оценка",
            "кандидат",
            "сила",
            "Hподд",
            "Vподд",
            "помехУр",
            "времян.",
            "воздерж.",
            "кэш",
            "морф.пров",
            "геом.пров",
        ]
    return [
        "frame",
        "time",
        "quality",
        "trace",
        "branches",
        "interf.",
        "H",
        "V",
        "assess",
        "candidate",
        "strength",
        "Hsup",
        "Vsup",
        "interfL",
        "temporal",
        "abstention",
        "cache",
        "morph_rev",
        "geom_rev",
    ]


def profile_label(profile: str, language: str) -> str:
    ru = language == "ru"
    if profile == "compact":
        return "Компактная таблица" if ru else "Compact table"
    return "Полная таблица" if ru else "Full table"


def visible_columns_for_profile(profile: str) -> tuple[int, ...]:
    if profile == "full":
        return FULL_VISIBLE_COLUMNS
    return COMPACT_VISIBLE_COLUMNS


def default_min_widths(font: QFont | None = None) -> dict[int, int]:
    """Readable minimum widths from font metrics (not blind constants)."""
    if font is not None:
        fm = QFontMetrics(font)
        em = max(fm.horizontalAdvance("M"), 8)
        pad = max(fm.horizontalAdvance("00"), em) + 12
    else:
        # Safe fallback when no QApplication/font is available (unit tests / early init).
        em = 10
        pad = 22

    def chars(n: float) -> int:
        return int(em * n + pad)

    return {
        SEQ_COL_FRAME: chars(3.5),
        SEQ_COL_TIME: chars(5.5),
        SEQ_COL_QUALITY: chars(8),
        SEQ_COL_TRACE: chars(4),
        SEQ_COL_BRANCHES: chars(4),
        SEQ_COL_INTERF: chars(6),
        SEQ_COL_H: chars(5),
        SEQ_COL_V: chars(5),
        SEQ_COL_ASSESS: chars(8),
        SEQ_COL_CANDIDATE: chars(10),
        SEQ_COL_STRENGTH: chars(7),
        SEQ_COL_HSUP: chars(5),
        SEQ_COL_VSUP: chars(5),
        SEQ_COL_INTERFL: chars(6),
        SEQ_COL_TEMPORAL: chars(6),
        SEQ_COL_ABSTENTION: chars(10),
        SEQ_COL_CACHE: chars(8),
        SEQ_COL_MORPH_REV: chars(8),
        SEQ_COL_GEOM_REV: chars(8),
    }


def preferred_widths(font: QFont | None = None) -> dict[int, int]:
    """Initial preferred widths (Interactive; user may resize)."""
    mins = default_min_widths(font)
    # Slightly wider defaults for content-aware columns.
    out = dict(mins)
    out[SEQ_COL_QUALITY] = int(mins[SEQ_COL_QUALITY] * 1.25)
    out[SEQ_COL_ASSESS] = int(mins[SEQ_COL_ASSESS] * 1.2)
    out[SEQ_COL_CANDIDATE] = int(mins[SEQ_COL_CANDIDATE] * 1.35)
    out[SEQ_COL_STRENGTH] = int(mins[SEQ_COL_STRENGTH] * 1.15)
    out[SEQ_COL_INTERF] = int(mins[SEQ_COL_INTERF] * 1.15)
    out[SEQ_COL_ABSTENTION] = int(mins[SEQ_COL_ABSTENTION] * 1.4)
    return out


def marker_colors(
    *,
    displayed: bool,
    failed: bool,
    processing: bool,
    last_completed: bool,
    cached: bool,
    theme: ThemeName | None = None,
) -> SeqPropMarkerColors:
    """Subtle background markers with strong theme-aware foreground contrast."""
    t = theme or resolve_theme_name()
    tokens = source_card_tokens(t)
    fg = QColor(tokens["text"])
    if t == "dark":
        if displayed:
            return SeqRowMarkerColors(QColor("#1e3a5f"), fg)
        if failed:
            return SeqRowMarkerColors(QColor("#4a2222"), fg)
        if processing:
            return SeqRowMarkerColors(QColor("#3d3420"), fg)
        if last_completed:
            return SeqRowMarkerColors(QColor("#1e4d2b"), fg)
        if cached:
            return SeqRowMarkerColors(QColor("#2a2d33"), fg)
        return SeqRowMarkerColors(QColor("#252930"), fg)
    # light
    if displayed:
        return SeqRowMarkerColors(QColor("#dceaf8"), fg)
    if failed:
        return SeqRowMarkerColors(QColor("#fde0e0"), fg)
    if processing:
        return SeqRowMarkerColors(QColor("#fff3d6"), fg)
    if last_completed:
        return SeqRowMarkerColors(QColor("#d8f0df"), fg)
    if cached:
        return SeqRowMarkerColors(QColor("#eef0f3"), fg)
    return SeqRowMarkerColors(QColor("#ffffff"), fg)
