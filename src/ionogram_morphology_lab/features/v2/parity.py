"""Python mirrors of MATLAB V2 geometric helpers for parity fixtures."""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.interference import stripe_burden_summary
from ionogram_morphology_lab.features.v2.widths import _percentile_width


def _reject_nonfinite(profile: np.ndarray) -> dict[str, Any] | None:
    p = np.asarray(profile, dtype=float).ravel()
    if p.size == 0:
        return {
            "value": None,
            "valid": False,
            "estimator": "robust_percentile",
            "reason_invalid": "insufficient_coverage",
        }
    if not np.isfinite(p).all():
        return {
            "value": None,
            "valid": False,
            "estimator": "robust_percentile",
            "reason_invalid": "nonfinite_input",
        }
    return None


def local_vertical_width(profile: np.ndarray) -> dict[str, Any]:
    bad = _reject_nonfinite(profile)
    if bad is not None:
        return bad
    p = np.asarray(profile, dtype=float).ravel()
    p = np.clip(p - np.median(p), 0, None)
    val, reason = _percentile_width(p)
    return {
        "value": val,
        "valid": val is not None,
        "estimator": "robust_percentile",
        "reason_invalid": reason,
    }


def local_horizontal_width(profile: np.ndarray) -> dict[str, Any]:
    bad = _reject_nonfinite(profile)
    if bad is not None:
        bad["estimator"] = "robust_percentile_slope_compensated"
        return bad
    p = np.asarray(profile, dtype=float).ravel()
    p = np.clip(p - np.median(p), 0, None)
    val, reason = _percentile_width(p)
    if val is None:
        return {
            "value": None,
            "valid": False,
            "estimator": "robust_percentile_slope_compensated",
            "reason_invalid": reason,
        }
    return {
        "value": float(max(val - 1.0, 0.0)),
        "valid": True,
        "estimator": "robust_percentile_slope_compensated",
        "reason_invalid": "",
    }


def branch_separation(rows_a: np.ndarray, rows_b: np.ndarray) -> dict[str, Any]:
    a = np.asarray(rows_a, dtype=float).ravel()
    b = np.asarray(rows_b, dtype=float).ravel()
    if a.size == 0 or a.size != b.size:
        return {"value": None, "valid": False, "reason_invalid": "insufficient_coverage"}
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        return {"value": None, "valid": False, "reason_invalid": "nonfinite_input"}
    return {"value": float(np.median(np.abs(a - b))), "valid": True, "reason_invalid": ""}


def interference_stripe_burden(mask: np.ndarray) -> dict[str, float]:
    return stripe_burden_summary(np.asarray(mask).astype(bool))
