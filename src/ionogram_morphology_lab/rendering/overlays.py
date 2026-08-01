"""Visual layer/morphology overlays — color + line style + labels (not color alone)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class OverlaySpec:
    key: str
    label_en: str
    label_ru: str
    color: str  # hex
    linestyle: str  # solid | dashed | dotted
    pattern: str  # hatch-like marker for accessibility
    enabled: bool = True


DEFAULT_OVERLAYS = [
    OverlaySpec("E", "E trace", "Трасса E", "#1f77b4", "solid", "///"),
    OverlaySpec("Es", "Es trace", "Трасса Es", "#ff7f0e", "dashed", "xxx"),
    OverlaySpec("F1", "F1 trace", "Трасса F1", "#2ca02c", "solid", "..."),
    OverlaySpec("F2", "F2 trace", "Трасса F2", "#d62728", "solid", "+++"),
    OverlaySpec("uncertain", "Uncertain trace", "Неуверенная трасса", "#9467bd", "dotted", "???"),
    OverlaySpec("interference", "Interference", "Помехи", "#8c564b", "dashed", "|||"),
    OverlaySpec("ox_branch", "O/X candidate branches", "Кандидаты O/X", "#e377c2", "dotted", "ooo"),
    OverlaySpec("frequency_spread", "Frequency-spread region", "Частотное рассеяние", "#17becf", "dashed", "==="),
    OverlaySpec("range_spread", "Range-spread region", "Высотное рассеяние", "#bcbd22", "dashed", "---"),
    OverlaySpec("mixed_spread", "Mixed-spread region", "Смешанное рассеяние", "#7f7f7f", "dotted", "***"),
]


def overlay_legend(lang: str = "en") -> list[dict[str, Any]]:
    rows = []
    for o in DEFAULT_OVERLAYS:
        rows.append(
            {
                "key": o.key,
                "label": o.label_ru if lang == "ru" else o.label_en,
                "color": o.color,
                "linestyle": o.linestyle,
                "pattern": o.pattern,
                "enabled": o.enabled,
            }
        )
    return rows


def compose_overlay_rgba(
    base_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    enabled: dict[str, bool] | None = None,
    alpha: float = 0.35,
) -> np.ndarray:
    """Compose overlays onto an RGB image; raw base remains visible underneath."""
    out = np.asarray(base_rgb, dtype=float).copy()
    if out.ndim == 2:
        out = np.stack([out, out, out], axis=-1)
    color_map = {
        "E": (0.12, 0.47, 0.71),
        "Es": (1.0, 0.50, 0.05),
        "F1": (0.17, 0.63, 0.17),
        "F2": (0.84, 0.15, 0.16),
        "uncertain": (0.58, 0.40, 0.74),
        "interference": (0.55, 0.34, 0.29),
        "ox_branch": (0.89, 0.47, 0.76),
        "frequency_spread": (0.09, 0.75, 0.81),
        "range_spread": (0.74, 0.74, 0.13),
        "mixed_spread": (0.50, 0.50, 0.50),
    }
    enabled = enabled or {k: True for k in color_map}
    for key, mask in masks.items():
        if not enabled.get(key, True):
            continue
        if mask is None:
            continue
        m = np.asarray(mask).astype(bool)
        if m.shape[:2] != out.shape[:2]:
            continue
        col = color_map.get(key, (1.0, 1.0, 0.0))
        for c in range(3):
            channel = out[..., c]
            channel[m] = (1 - alpha) * channel[m] + alpha * col[c] * 255.0
            out[..., c] = channel
    return np.clip(out, 0, 255).astype(np.uint8)
