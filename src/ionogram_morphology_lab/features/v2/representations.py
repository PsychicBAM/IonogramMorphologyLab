"""Raw vs derived diagnostic representations — never overwrite raw."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import DerivedRepresentation, FEATURE_VERSION


def _hash_array(arr: np.ndarray) -> str:
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()[:16]


def build_representations(raw: np.ndarray) -> dict[str, DerivedRepresentation]:
    raw_arr = np.asarray(raw)
    in_hash = _hash_array(raw_arr)

    # Diagnostic normalization: robust percentile stretch (diagnostic only)
    x = raw_arr.astype(np.float64, copy=True)
    finite = np.isfinite(x)
    params = {"method": "robust_percentile_stretch", "lo": 2.0, "hi": 98.0}
    if finite.any():
        lo, hi = np.percentile(x[finite], [params["lo"], params["hi"]])
        if hi <= lo:
            hi = lo + 1.0
        y = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
        y[~finite] = 0.0
    else:
        y = np.zeros_like(x)
        lo, hi = 0.0, 1.0
    params["lo_value"] = float(lo)
    params["hi_value"] = float(hi)

    # Contrast prep: column-median subtract only.
    # Full row-median subtract zeros continuous horizontal ridges (median≈peak).
    bg = np.median(x, axis=0, keepdims=True)
    score = x - bg
    score_params: dict[str, Any] = {
        "method": "column_median_subtract",
        "note": "row_median_subtract_disabled_to_preserve_horizontal_ridges",
    }

    reps = {
        "raw": DerivedRepresentation(
            name="raw",
            method="identity",
            version=FEATURE_VERSION,
            parameters={},
            input_hash=in_hash,
            output_hash=in_hash,
            status="scientific",
            array=raw_arr.copy(),
        ),
        "diagnostic_normalized": DerivedRepresentation(
            name="diagnostic_normalized",
            method=params["method"],
            version=FEATURE_VERSION,
            parameters=params,
            input_hash=in_hash,
            output_hash=_hash_array(y),
            status="diagnostic",
            array=y,
        ),
        "signal_background_score": DerivedRepresentation(
            name="signal_background_score",
            method=score_params["method"],
            version=FEATURE_VERSION,
            parameters=score_params,
            input_hash=in_hash,
            output_hash=_hash_array(score),
            status="diagnostic",
            array=score,
        ),
    }
    return reps
