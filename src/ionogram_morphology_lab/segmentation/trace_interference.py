"""Interpretable trace / interference segmentation (heuristic, probabilistic)."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

import numpy as np


@dataclass
class SegmentationResult:
    trace_mask: np.ndarray
    interference_mask: np.ndarray
    ridge_map: np.ndarray
    skeleton: np.ndarray
    component_map: np.ndarray
    method: str
    parameters: dict[str, Any]
    version: str = "iml1-0.1.0"
    limitations: str = (
        "Heuristic segmentation. Brightest structure is not assumed to be the ionospheric trace. "
        "Interference detection is probabilistic unless validated. "
        "Not a confirmed physical mode separation."
    )
    reproducibility: dict[str, Any] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "parameters": self.parameters,
            "version": self.version,
            "limitations": self.limitations,
            "reproducibility": self.reproducibility,
        }


def _robust_threshold(arr: np.ndarray, k: float = 3.0) -> float:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 0.0
    med = float(np.median(finite))
    mad = float(np.median(np.abs(finite - med))) + 1e-9
    return med + k * 1.4826 * mad


def segment_frame(frame: np.ndarray, percentile: float = 92.0) -> SegmentationResult:
    """
    Produce candidate masks without modifying the raw frame.
    Vertical-stripe interference: narrow frequency-localized columns with
    near-full-height persistence.
    """
    arr = np.asarray(frame, dtype=np.float64)
    h, w = arr.shape
    finite = np.isfinite(arr)
    work = np.where(finite, arr, 0.0)

    thr = float(np.percentile(work[finite], percentile)) if finite.any() else 0.0
    thr = max(thr, _robust_threshold(work))
    bright = work >= thr

    # Vertical interference heuristic
    col_frac = bright.mean(axis=0)
    interference_cols = col_frac >= 0.55
    # narrow: isolated or small groups
    interference_mask = np.zeros_like(bright, dtype=bool)
    interference_mask[:, interference_cols] = bright[:, interference_cols]

    # Trace candidate = bright minus interference-dominated columns
    trace_mask = bright & ~interference_mask

    # Simple ridge: row-wise local maxima among trace
    ridge = np.zeros_like(work)
    for i in range(h):
        row = work[i]
        if not np.any(trace_mask[i]):
            continue
        j = int(np.argmax(np.where(trace_mask[i], row, -np.inf)))
        if np.isfinite(row[j]):
            ridge[i, j] = row[j]

    # Skeleton approximation: thin vertical/horizontal via morphological-like keep
    try:
        from skimage.morphology import skeletonize

        skeleton = skeletonize(trace_mask)
    except Exception:  # noqa: BLE001
        skeleton = ridge > 0

    # Connected components
    try:
        from skimage.measure import label

        component_map = label(trace_mask, connectivity=2)
    except Exception:  # noqa: BLE001
        component_map = trace_mask.astype(np.int32)

    return SegmentationResult(
        trace_mask=trace_mask,
        interference_mask=interference_mask,
        ridge_map=ridge,
        skeleton=np.asarray(skeleton, dtype=bool),
        component_map=np.asarray(component_map),
        method="percentile_threshold_plus_vertical_stripe",
        parameters={"percentile": percentile, "vert_col_frac": 0.55},
        reproducibility={"seed": None, "deterministic": True},
    )
