"""Numeric quality gates before V2 trace extraction.

All thresholds below are project heuristics for assessability routing.
They are not physical morphology classifications.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import MeasuredFeature

# Project heuristics (documented)
HEUR_FINITE_NOT_ASSESSABLE = 0.5
HEUR_ZERO_NOT_ASSESSABLE = 0.995
HEUR_SAT_NOT_ASSESSABLE = 0.90
HEUR_STRIPE_INTERFERENCE_LIMITED = 0.35
HEUR_FINITE_DEGRADED = 0.95
HEUR_SAT_DEGRADED = 0.35
HEUR_IMPULSE_DEGRADED = 0.08
# Floor burden: only extreme lower-band dominance degrades the *frame*;
# ordinary lower-edge structure is handled in trace extraction instead.
HEUR_FLOOR_EXTREME_DEGRADED = 0.85


def assess_frame_quality(raw: np.ndarray) -> tuple[str, dict[str, MeasuredFeature], dict[str, Any]]:
    arr = np.asarray(raw)
    feats: dict[str, MeasuredFeature] = {}
    meta: dict[str, Any] = {
        "thresholds_are_project_heuristics": True,
        "heuristics": {
            "finite_not_assessable": HEUR_FINITE_NOT_ASSESSABLE,
            "zero_not_assessable": HEUR_ZERO_NOT_ASSESSABLE,
            "sat_not_assessable": HEUR_SAT_NOT_ASSESSABLE,
            "stripe_interference_limited": HEUR_STRIPE_INTERFERENCE_LIMITED,
            "finite_degraded": HEUR_FINITE_DEGRADED,
            "sat_degraded": HEUR_SAT_DEGRADED,
            "impulse_degraded": HEUR_IMPULSE_DEGRADED,
            "floor_extreme_degraded": HEUR_FLOOR_EXTREME_DEGRADED,
        },
    }

    if arr.ndim != 2 or arr.size == 0:
        feats["v2_quality_status"] = MeasuredFeature(
            "v2_quality_status", "not_assessable", unit="categorical",
            valid=True, confidence_status="high", metadata={"cause": "wrong_shape"},
        )
        return "not_assessable", feats, {"shape": list(arr.shape)}

    h, w = arr.shape
    finite = np.isfinite(arr.astype(float, copy=False))
    n = arr.size
    finite_frac = float(finite.mean()) if n else 0.0
    zeros = float(np.mean(arr == 0)) if n else 1.0
    vals = arr[finite].astype(float) if finite.any() else np.array([], dtype=float)
    if vals.size:
        p1, p50, p99 = np.percentile(vals, [1, 50, 99])
        vmax = float(vals.max())
        vmin = float(vals.min())
        sat = float(np.mean(vals >= 0.999 * vmax)) if vmax > vmin else 1.0
        dyn = float(vmax - vmin)
    else:
        p1 = p50 = p99 = sat = dyn = 0.0
        vmax = vmin = 0.0

    row_bg = np.median(arr.astype(float), axis=1) if h else np.array([])
    col_bg = np.median(arr.astype(float), axis=0) if w else np.array([])
    if vals.size > 10:
        iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
        impulse = float(np.mean(vals > (p99 + 3 * max(iqr, 1e-9))))
    else:
        impulse = 0.0

    if w and vals.size:
        stripe_thr = p50 + 2 * max(float(np.std(vals)), 1e-9)
        full_heightish = []
        for j in range(w):
            col = arr[:, j].astype(float)
            above = np.mean(col > stripe_thr) if np.isfinite(col).any() else 0.0
            full_heightish.append(above > 0.7)
        stripe_burden = float(np.mean(full_heightish))
        stripe_count = int(np.sum(full_heightish))
    else:
        stripe_burden = 0.0
        stripe_count = 0

    # Floor burden: elevated fraction in lower band *relative to mid-frame*,
    # not raw "above p50" which is near-always high on real Amp_all.
    floor_rows = max(1, h // 12)
    mid = arr[floor_rows : max(floor_rows + 1, 3 * h // 4), :].astype(float)
    floor = arr[:floor_rows, :].astype(float)
    if floor.size and mid.size and vals.size:
        mid_p75 = float(np.percentile(mid, 75))
        floor_elev = float(np.mean(floor > mid_p75))
        # Extreme only when almost the entire lower band is brighter than mid-frame
        floor_clutter = floor_elev
    else:
        floor_clutter = 0.0
    empty_frac = float(np.mean(arr.astype(float) <= p1)) if vals.size else 1.0
    row_bg_burden = float(np.std(row_bg) / (np.median(np.abs(row_bg)) + 1e-9)) if row_bg.size else 0.0
    col_bg_burden = float(np.std(col_bg) / (np.median(np.abs(col_bg)) + 1e-9)) if col_bg.size else 0.0

    meta.update(
        {
            "shape": [h, w],
            "dtype": str(arr.dtype),
            "finite_fraction": finite_frac,
            "zero_fraction": zeros,
            "saturation_fraction": sat,
            "dynamic_range": dyn,
            "percentiles": {"p1": float(p1), "p50": float(p50), "p99": float(p99)},
            "row_background_burden": row_bg_burden,
            "column_background_burden": col_bg_burden,
            "impulsive_outlier_fraction": impulse,
            "full_height_stripe_burden": stripe_burden,
            "full_height_stripe_count": stripe_count,
            "floor_clutter_burden": floor_clutter,
            "empty_region_fraction": empty_frac,
            "floor_note": "Ordinary lower-edge structure does not auto-degrade; extreme floor dominance may.",
        }
    )

    def _f(fid: str, val: float, unit: str = "fraction") -> None:
        feats[fid] = MeasuredFeature(fid, val, unit=unit, valid=True, confidence_status="high")

    _f("v2_finite_fraction", finite_frac)
    _f("v2_zero_fraction", zeros)
    _f("v2_saturation_fraction", sat)
    _f("v2_dynamic_range", dyn, unit="amplitude")
    _f("v2_robust_percentile_p1", float(p1), unit="amplitude")
    _f("v2_robust_percentile_p50", float(p50), unit="amplitude")
    _f("v2_robust_percentile_p99", float(p99), unit="amplitude")
    _f("v2_row_background_burden", row_bg_burden, unit="ratio")
    _f("v2_column_background_burden", col_bg_burden, unit="ratio")
    _f("v2_impulsive_outlier_fraction", impulse)
    _f("v2_full_height_stripe_burden", stripe_burden)
    _f("v2_floor_clutter_burden", floor_clutter)
    _f("v2_empty_region_fraction", empty_frac)

    if (
        finite_frac < HEUR_FINITE_NOT_ASSESSABLE
        or zeros > HEUR_ZERO_NOT_ASSESSABLE
        or (vals.size and dyn <= 0)
        or sat >= HEUR_SAT_NOT_ASSESSABLE
    ):
        status = "not_assessable"
    elif stripe_burden > HEUR_STRIPE_INTERFERENCE_LIMITED:
        status = "interference_limited"
    elif (
        finite_frac < HEUR_FINITE_DEGRADED
        or sat > HEUR_SAT_DEGRADED
        or impulse > HEUR_IMPULSE_DEGRADED
        or floor_clutter > HEUR_FLOOR_EXTREME_DEGRADED
    ):
        status = "degraded"
    else:
        status = "assessable"

    feats["v2_quality_status"] = MeasuredFeature(
        "v2_quality_status", status, unit="categorical", valid=True, confidence_status="high",
        metadata={"gates": meta},
    )
    return status, feats, meta
