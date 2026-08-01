"""Optional diagnostic normalization — never applied silently to raw view."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import numpy as np


@dataclass
class NormalizationResult:
    matrix: np.ndarray
    method: str
    parameters: dict[str, Any]
    version: str = "iml1-0.1.0"
    limitations: str = (
        "Comparison-only normalization. Not a physical recalibration. "
        "Excluded from raw view. Reversible relative to recorded parameters."
    )
    label: str = "DERIVED_DIAGNOSTIC"

    def metadata(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("matrix")
        return d


def normalize_for_comparison(
    frame: np.ndarray,
    method: str = "robust_percentile",
    p_low: float = 1.0,
    p_high: float = 99.0,
    shared_limits: tuple[float, float] | None = None,
) -> NormalizationResult:
    """
    Explicit, labeled normalization for similarity/comparison only.
    Default scientific mode does not call this for raw rendering.
    """
    arr = np.asarray(frame, dtype=np.float64).copy()
    finite = np.isfinite(arr)
    if method == "identity":
        return NormalizationResult(
            matrix=arr,
            method=method,
            parameters={},
        )
    if shared_limits is not None:
        lo, hi = shared_limits
    else:
        vals = arr[finite]
        if vals.size == 0:
            lo, hi = 0.0, 1.0
        else:
            lo = float(np.percentile(vals, p_low))
            hi = float(np.percentile(vals, p_high))
            if hi <= lo:
                hi = lo + 1.0
    out = np.zeros_like(arr)
    out[finite] = np.clip((arr[finite] - lo) / (hi - lo), 0.0, 1.0)
    out[~finite] = np.nan
    return NormalizationResult(
        matrix=out,
        method=method,
        parameters={"p_low": p_low, "p_high": p_high, "lo": lo, "hi": hi},
    )
