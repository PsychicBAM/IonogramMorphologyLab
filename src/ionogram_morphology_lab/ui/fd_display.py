"""Feature Diagnostics display helpers — orientation-safe raster composition."""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage

from ionogram_morphology_lab.rendering.display_transform import (
    DisplayOrientationIdentity,
    apply_display_transform,
    default_kfu_display_identity,
    transform_centerline_points,
    transform_mask_for_display,
)


def _percentile_u8(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float64)
    finite = np.isfinite(a)
    if finite.any():
        lo, hi = np.percentile(a[finite], [2, 98])
        if hi <= lo:
            hi = lo + 1
        n = np.clip((a - lo) / (hi - lo), 0, 1)
    else:
        n = np.zeros_like(a)
    return np.ascontiguousarray((n * 255).astype(np.uint8))


def scientific_to_display_gray(
    scientific: np.ndarray,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    """Scientific matrix → display-oriented uint8 grayscale (row0 at bottom visually)."""
    disp = apply_display_transform(scientific, identity=identity)
    return _percentile_u8(disp)


def gray_to_qimage(u8: np.ndarray) -> QImage:
    u8 = np.ascontiguousarray(u8)
    h, w = u8.shape
    return QImage(u8.data, w, h, w, QImage.Format.Format_Grayscale8).copy()


def overlay_rgba(h: int, w: int, mask_display: np.ndarray, rgba: tuple[int, int, int, int]) -> np.ndarray:
    out = np.zeros((h, w, 4), dtype=np.uint8)
    m = np.asarray(mask_display).astype(bool)
    if m.shape != (h, w):
        return out
    out[m, 0] = rgba[0]
    out[m, 1] = rgba[1]
    out[m, 2] = rgba[2]
    out[m, 3] = rgba[3]
    return out


def compose_rgb(base_u8: np.ndarray, overlays: list[np.ndarray], opacity: float) -> np.ndarray:
    g = base_u8.astype(np.float64)
    rgb = np.stack([g, g, g], axis=-1)
    for ov in overlays:
        if ov is None or ov.size == 0:
            continue
        a = (ov[..., 3:4].astype(np.float64) / 255.0) * opacity
        col = ov[..., :3].astype(np.float64)
        rgb = rgb * (1 - a) + col * a
    return np.ascontiguousarray(np.clip(rgb, 0, 255).astype(np.uint8))


def jet_like_rgb(scientific: np.ndarray, *, identity: DisplayOrientationIdentity | None = None) -> np.ndarray:
    """Approximate Viewer jet colormap on display-oriented frame (visual only)."""
    disp = apply_display_transform(scientific, identity=identity)
    a = np.asarray(disp, dtype=np.float64)
    finite = np.isfinite(a)
    out = np.zeros(a.shape + (3,), dtype=np.uint8)
    if not finite.any():
        return out
    lo, hi = np.percentile(a[finite], [1, 99])
    if hi <= lo:
        hi = lo + 1
    t = np.clip((a - lo) / (hi - lo), 0, 1)
    # Simple jet-like piecewise
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    out[..., 0] = (r * 255).astype(np.uint8)
    out[..., 1] = (g * 255).astype(np.uint8)
    out[..., 2] = (b * 255).astype(np.uint8)
    out[~finite] = 0
    return np.ascontiguousarray(out)


def prepare_overlay_mask(
    scientific_mask: np.ndarray,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    return transform_mask_for_display(scientific_mask, identity=identity)


def prepare_centerline_mask(
    centerlines: list,
    h: int,
    w: int,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    cl = np.zeros((h, w), dtype=bool)
    for item in centerlines:
        pts = getattr(item, "points_rc", None)
        if pts is None and isinstance(item, dict):
            pts = item.get("points_rc") or []
        disp_pts = transform_centerline_points(list(pts or []), h, w, identity=identity)
        for r, c in disp_pts:
            if 0 <= r < h and 0 <= c < w:
                cl[r, c] = True
    return cl


def orientation_identity_dict() -> dict:
    return default_kfu_display_identity().to_dict()
