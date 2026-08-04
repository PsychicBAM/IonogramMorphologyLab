"""Canonical display orientation for Viewer and Feature Diagnostics (Phase 4B.2e).

Scientific matrices are never mutated for UI repair. Display transforms are applied
only when building raster images, overlays, and export PNGs.

KFU convention (matches matplotlib ``origin="lower"`` in Ionogram Viewer):
- scientific row 0 = lowest nominal virtual height (floor band near row 0);
- on screen, that row appears at the **bottom**;
- raster buffers (QImage, PNG top-left) therefore apply a vertical flip.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

TRANSFORM_VERSION = "iml-display-v1"


@dataclass(frozen=True)
class DisplayOrientationIdentity:
    """Provenance for display vs scientific orientation."""

    matrix_origin: str = "row0_low_nominal_height"
    display_origin: str = "image_top_left"
    row_zero_display_location: str = "bottom"
    vertical_flip_applied: bool = True
    horizontal_flip_applied: bool = False
    transform_version: str = TRANSFORM_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_kfu_display_identity() -> DisplayOrientationIdentity:
    return DisplayOrientationIdentity()


def apply_display_transform(
    array: np.ndarray,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    """Return a **new** array oriented for top-left raster display (QImage / PNG).

    Does not modify ``array``. Scientific consumers must keep using the original.
    """
    ident = identity or default_kfu_display_identity()
    out = np.asarray(array)
    if ident.vertical_flip_applied:
        out = np.flipud(out)
    if ident.horizontal_flip_applied:
        out = np.fliplr(out)
    return np.ascontiguousarray(out)


def invert_display_transform(
    array: np.ndarray,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    """Map a display-oriented array back to scientific orientation (copy)."""
    return apply_display_transform(array, identity=identity)


def transform_rc_scientific_to_display(
    row: int,
    col: int,
    height: int,
    width: int,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> tuple[int, int]:
    """Map scientific (row, col) → display pixel (row, col) for overlays."""
    ident = identity or default_kfu_display_identity()
    r, c = int(row), int(col)
    if ident.vertical_flip_applied:
        r = (height - 1) - r
    if ident.horizontal_flip_applied:
        c = (width - 1) - c
    return r, c


def transform_mask_for_display(
    mask: np.ndarray,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> np.ndarray:
    return apply_display_transform(mask, identity=identity)


def transform_centerline_points(
    points_rc: list[tuple[int, int]],
    height: int,
    width: int,
    *,
    identity: DisplayOrientationIdentity | None = None,
) -> list[tuple[int, int]]:
    return [
        transform_rc_scientific_to_display(r, c, height, width, identity=identity)
        for r, c in points_rc
    ]


def matplotlib_imshow_origin(identity: DisplayOrientationIdentity | None = None) -> str:
    """Origin string for matplotlib when plotting the **scientific** matrix directly."""
    ident = identity or default_kfu_display_identity()
    # Scientific matrix + origin lower ≡ flipud + origin upper
    if ident.vertical_flip_applied and not ident.horizontal_flip_applied:
        return "lower"
    return "upper"


def orientation_parity_corners(h: int, w: int) -> dict[str, tuple[int, int]]:
    """Scientific corner coordinates used by parity tests."""
    return {
        "top_left_display_scientific_rc": (h - 1, 0),  # appears top-left after flipud
        "top_right_display_scientific_rc": (h - 1, w - 1),
        "bottom_left_display_scientific_rc": (0, 0),
        "bottom_right_display_scientific_rc": (0, w - 1),
        "scientific_row0_col0": (0, 0),
        "scientific_last_row_last_col": (h - 1, w - 1),
    }
