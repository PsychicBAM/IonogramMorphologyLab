"""Synthetic geometry fixtures for algorithm tests — not physical ionograms.

Anisotropic broadening fixtures use a ~45° diagonal thin baseline so that
both fixed-frequency (H) and fixed-range (V) transverse cuts are identifiable
over a documented interior region. Broadening is applied with explicit
separable kernels along one axis at a time.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def _blank(h: int = 128, w: int = 200, dtype=np.float64) -> np.ndarray:
    return np.zeros((h, w), dtype=dtype)


def thin_horizontal_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    a = _blank(h, w)
    r = h // 3
    a[r : r + 2, 20:180] = 100
    return a


def thin_sloping_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    a = _blank(h, w)
    for c in range(20, 180):
        r = int(30 + 0.35 * (c - 20))
        if 0 <= r < h - 1:
            a[r : r + 2, c] = 100
    return a


def thin_curved_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    a = _blank(h, w)
    for c in range(20, 180):
        r = int(40 + 18 * np.sin((c - 20) / 25.0))
        if 0 <= r < h - 1:
            a[r : r + 2, c] = 100
    return a


def thin_diagonal_baseline(h: int = 128, w: int = 200) -> np.ndarray:
    """~45° thin ridge — both fixed-axis transverse cuts identifiable (heuristic)."""
    a = _blank(h, w)
    for c in range(25, 165):
        r = int(20 + 1.0 * (c - 25))
        if 0 <= r < h - 1:
            a[r : r + 2, c] = 100
    return a


def thin_steep_baseline(h: int = 128, w: int = 200) -> np.ndarray:
    """Steep thin ridge (slope~1.8): fixed-H transverse applicable; fixed-V near-tangent."""
    a = _blank(h, w)
    for c in range(40, 110):
        r = int(15 + 1.8 * (c - 40))
        if 0 <= r < h - 2:
            a[r : r + 3, c] = 120
    return a


def thin_shallow_baseline(h: int = 128, w: int = 200) -> np.ndarray:
    """Shallow thin ridge (slope~0.15): fixed-V transverse applicable; fixed-H near-tangent."""
    a = _blank(h, w)
    for c in range(25, 175):
        r = int(50 + 0.15 * (c - 25))
        if 0 <= r < h - 1:
            a[r : r + 2, c] = 100
    return a


def frequency_axis_broadened_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    """Broaden steep baseline along fixed frequency/X only (known support geometry).

    Paired thin baseline: thin_steep_baseline. Fixed-H identifiable; fixed-V expected
    invalid (axis_tangent). Documented region: columns 45–105.
    """
    a = _blank(h, w)
    for c in range(40, 110):
        r = int(15 + 1.8 * (c - 40))
        if not (0 <= r < h - 2):
            continue
        for dc in range(-8, 9):
            cc = c + dc
            if 0 <= cc < w:
                amp = 120.0 * float(np.exp(-0.5 * (dc / 2.5) ** 2))
                a[r : r + 3, cc] = np.maximum(a[r : r + 3, cc], amp)
    return a


def range_axis_broadened_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    """Broaden shallow baseline along fixed range/Y only (known support geometry).

    Paired thin baseline: thin_shallow_baseline. Fixed-V identifiable; fixed-H expected
    invalid (axis_tangent). Documented region: columns 40–160.
    """
    a = _blank(h, w)
    for c in range(25, 175):
        r = int(50 + 0.15 * (c - 25))
        if not (0 <= r < h):
            continue
        for dr in range(-8, 9):
            rr = r + dr
            if 0 <= rr < h:
                amp = 100.0 * float(np.exp(-0.5 * (dr / 2.5) ** 2))
                a[rr, c] = max(float(a[rr, c]), amp)
    return a


def both_axes_broadened_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    """Broaden diagonal baseline independently along both fixed axes (max of axis paints)."""
    a = _blank(h, w)
    for c in range(25, 165):
        r = int(20 + 1.0 * (c - 25))
        if not (0 <= r < h - 1):
            continue
        for dc in range(-6, 7):
            cc = c + dc
            if 0 <= cc < w:
                amp = 100.0 * float(np.exp(-0.5 * (dc / 2.0) ** 2))
                a[r : r + 2, cc] = np.maximum(a[r : r + 2, cc], amp)
        for dr in range(-6, 7):
            rr = r + dr
            if 0 <= rr < h:
                amp = 100.0 * float(np.exp(-0.5 * (dr / 2.0) ** 2))
                a[rr, c] = max(float(a[rr, c]), amp)
    return a


# Legacy names — map to scientifically transparent anisotropic fixtures
def vertically_broadened_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    return range_axis_broadened_ridge(h, w)


def horizontally_broadened_ridge(h: int = 128, w: int = 200) -> np.ndarray:
    return frequency_axis_broadened_ridge(h, w)


def broadened_both_axes(h: int = 128, w: int = 200) -> np.ndarray:
    return both_axes_broadened_ridge(h, w)


def two_parallel_branches(h: int = 128, w: int = 200) -> np.ndarray:
    a = _blank(h, w)
    for c in range(25, 175):
        r1 = 40
        r2 = 55
        a[r1 : r1 + 2, c] = 100
        a[r2 : r2 + 2, c] = 90
    return a


def crossing_branches(h: int = 128, w: int = 200) -> np.ndarray:
    a = _blank(h, w)
    for c in range(20, 180):
        r1 = int(30 + 0.3 * (c - 20))
        r2 = int(70 - 0.25 * (c - 20))
        if 0 <= r1 < h - 1:
            a[r1 : r1 + 2, c] = 100
        if 0 <= r2 < h - 1:
            a[r2 : r2 + 2, c] = 95
    return a


def vertical_interference_stripes(h: int = 128, w: int = 200) -> np.ndarray:
    a = thin_sloping_ridge(h, w)
    for c in (50, 51, 120, 121, 122):
        a[:, c] = 150
    return a


def full_height_stripe_clutter(h: int = 128, w: int = 200) -> np.ndarray:
    a = thin_horizontal_ridge(h, w)
    for c in range(40, 80):
        a[:, c] = 140
    return a


def partial_missing_trace(h: int = 128, w: int = 200) -> np.ndarray:
    a = thin_sloping_ridge(h, w)
    a[:, 80:110] = 0
    return a


def isolated_bright_impulses(h: int = 128, w: int = 200) -> np.ndarray:
    a = thin_horizontal_ridge(h, w)
    a[10, 10] = 200
    a[100, 150] = 200
    a[60, 90] = 200
    return a


def zero_frame(h: int = 128, w: int = 200) -> np.ndarray:
    return _blank(h, w)


def saturated_frame(h: int = 128, w: int = 200) -> np.ndarray:
    return np.full((h, w), 65535, dtype=np.float64)


GEOMETRY_CASES: dict[str, Callable[..., np.ndarray]] = {
    "thin_horizontal_ridge": thin_horizontal_ridge,
    "thin_sloping_ridge": thin_sloping_ridge,
    "thin_curved_ridge": thin_curved_ridge,
    "thin_diagonal_baseline": thin_diagonal_baseline,
    "thin_steep_baseline": thin_steep_baseline,
    "thin_shallow_baseline": thin_shallow_baseline,
    "vertically_broadened_ridge": vertically_broadened_ridge,
    "horizontally_broadened_ridge": horizontally_broadened_ridge,
    "broadened_both_axes": broadened_both_axes,
    "two_parallel_branches": two_parallel_branches,
    "crossing_branches": crossing_branches,
    "vertical_interference_stripes": vertical_interference_stripes,
    "full_height_stripe_clutter": full_height_stripe_clutter,
    "partial_missing_trace": partial_missing_trace,
    "isolated_bright_impulses": isolated_bright_impulses,
    "zero_frame": zero_frame,
    "saturated_frame": saturated_frame,
}


def generate_geometry_case(name: str, **kwargs) -> np.ndarray:
    if name not in GEOMETRY_CASES:
        raise KeyError(f"Unknown geometry case: {name}")
    return GEOMETRY_CASES[name](**kwargs)
