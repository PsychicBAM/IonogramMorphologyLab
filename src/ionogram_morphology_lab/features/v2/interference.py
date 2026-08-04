"""Interference as a separate measurement axis (not morphology replacement)."""

from __future__ import annotations

import numpy as np

from ionogram_morphology_lab.features.v2.types import MeasuredFeature


def measure_interference(
    interference_mask: np.ndarray,
    accepted_trace: np.ndarray,
    quality_status: str,
    *,
    plausible_pre_exclusion: np.ndarray | None = None,
) -> dict[str, MeasuredFeature]:
    feats: dict[str, MeasuredFeature] = {}
    h, w = interference_mask.shape
    if w == 0:
        feats["v2_interference_level"] = MeasuredFeature(
            "v2_interference_level", "none", unit="categorical", valid=True, confidence_status="high"
        )
        return feats

    col_frac = interference_mask.mean(axis=0)
    stripe_cols = col_frac > 0.55
    stripe_count = int(stripe_cols.sum())
    affected_freq_frac = float(stripe_cols.mean()) if w else 0.0

    widths = []
    run = 0
    for b in stripe_cols:
        if b:
            run += 1
        elif run:
            widths.append(run)
            run = 0
    if run:
        widths.append(run)
    stripe_width = float(np.median(widths)) if widths else 0.0
    persistence = float(col_frac[stripe_cols].mean()) if stripe_cols.any() else 0.0
    density = float(interference_mask.mean())

    plausible = plausible_pre_exclusion if plausible_pre_exclusion is not None else accepted_trace
    if plausible.any():
        potential_overlap = float((plausible & interference_mask).sum() / max(int(plausible.sum()), 1))
    else:
        potential_overlap = 0.0

    if accepted_trace.any():
        outside = float((accepted_trace & ~interference_mask).sum() / max(int(accepted_trace.sum()), 1))
        # Occluded: plausible under interference but not recovered in accepted
        occluded = float(((plausible & interference_mask) & ~accepted_trace).sum() / max(int(plausible.sum()), 1)) if plausible.any() else 0.0
        # Inferred continuation: accepted neighbors on both sides of a stripe column
        continued = 0
        stripe_idx = np.where(stripe_cols)[0]
        for j in stripe_idx:
            left = accepted_trace[:, max(0, j - 2) : j].any() if j > 0 else False
            right = accepted_trace[:, j + 1 : min(w, j + 3)].any() if j + 1 < w else False
            if left and right:
                continued += 1
        continuation_frac = float(continued / max(len(stripe_idx), 1)) if len(stripe_idx) else 0.0
    else:
        outside = None
        occluded = potential_overlap
        continuation_frac = 0.0

    if not accepted_trace.any() and (affected_freq_frac > 0.4 or quality_status == "not_assessable"):
        level = "prevents_assessment"
    elif accepted_trace.any() and outside is not None and outside < 0.15:
        level = "prevents_assessment"
    elif affected_freq_frac > 0.25 or density > 0.2:
        level = "dominant"
    elif affected_freq_frac > 0.1 or density > 0.08:
        level = "significant"
    elif stripe_count > 0 or density > 0.01:
        level = "present"
    else:
        level = "none"

    if level == "prevents_assessment" and accepted_trace.any() and outside is not None and outside >= 0.3:
        level = "significant"

    feats["v2_interference_level"] = MeasuredFeature(
        "v2_interference_level", level, unit="categorical", valid=True, confidence_status="medium",
        metadata={
            "stripe_count": stripe_count,
            "stripe_width_bins": stripe_width,
            "stripe_persistence": persistence,
            "stripe_density": density,
            "affected_frequency_fraction": affected_freq_frac,
            "potential_overlap_pre_exclusion": potential_overlap,
            "assessment_still_possible": level != "prevents_assessment",
        },
    )
    feats["v2_vertical_stripe_count"] = MeasuredFeature(
        "v2_vertical_stripe_count", float(stripe_count), unit="count", valid=True, confidence_status="medium",
    )
    feats["v2_interference_stripe_width"] = MeasuredFeature(
        "v2_interference_stripe_width", stripe_width, unit="bins", valid=True, confidence_status="medium",
    )
    feats["v2_interference_stripe_height_persistence"] = MeasuredFeature(
        "v2_interference_stripe_height_persistence", persistence, unit="fraction", valid=True, confidence_status="medium",
    )
    feats["v2_interference_stripe_amplitude"] = MeasuredFeature(
        "v2_interference_stripe_amplitude",
        float(col_frac[stripe_cols].max()) if stripe_cols.any() else 0.0,
        unit="fraction", valid=True, confidence_status="medium",
    )
    feats["v2_interference_stripe_density"] = MeasuredFeature(
        "v2_interference_stripe_density", density, unit="fraction", valid=True, confidence_status="medium",
    )
    feats["v2_interference_affected_frequency_fraction"] = MeasuredFeature(
        "v2_interference_affected_frequency_fraction", affected_freq_frac, unit="fraction",
        valid=True, confidence_status="medium",
    )
    feats["v2_potential_trace_interference_overlap"] = MeasuredFeature(
        "v2_potential_trace_interference_overlap", potential_overlap, unit="fraction",
        valid=True, confidence_status="medium",
        metadata={"measured_on": "plausible_pre_exclusion"},
    )
    feats["v2_inferred_continuation_across_interference"] = MeasuredFeature(
        "v2_inferred_continuation_across_interference", continuation_frac, unit="fraction",
        valid=True, confidence_status="low",
    )
    feats["v2_unresolved_occluded_fraction"] = MeasuredFeature(
        "v2_unresolved_occluded_fraction", float(occluded), unit="fraction",
        valid=True, confidence_status="medium",
    )

    if accepted_trace.any():
        # Overlap of *accepted* with interference should be near-zero by construction;
        # report separately from potential pre-exclusion overlap.
        post = float((accepted_trace & interference_mask).sum() / max(int(accepted_trace.sum()), 1))
        feats["v2_interference_trace_overlap"] = MeasuredFeature(
            "v2_interference_trace_overlap", post, unit="fraction",
            valid=True, confidence_status="medium",
            metadata={"note": "post_exclusion_accepted_overlap; prefer potential_pre_exclusion"},
        )
        feats["v2_usable_trace_fraction_outside_interference"] = MeasuredFeature(
            "v2_usable_trace_fraction_outside_interference", float(outside or 0.0), unit="fraction",
            valid=True, confidence_status="medium",
            metadata={"not_by_construction_claim": True, "potential_overlap": potential_overlap},
        )
    else:
        feats["v2_interference_trace_overlap"] = MeasuredFeature(
            "v2_interference_trace_overlap", None, unit="fraction", valid=False,
            reason_invalid="trace_not_found", confidence_status="abstain",
        )
        feats["v2_usable_trace_fraction_outside_interference"] = MeasuredFeature(
            "v2_usable_trace_fraction_outside_interference", None, unit="fraction", valid=False,
            reason_invalid="trace_not_found", confidence_status="abstain",
        )
    return feats


def stripe_burden_summary(interference_mask: np.ndarray) -> dict[str, float]:
    """Compact summary for MATLAB parity fixtures."""
    if interference_mask.size == 0:
        return {
            "stripe_count": 0.0,
            "stripe_widths_median": 0.0,
            "affected_frequency_fraction": 0.0,
            "persistence": 0.0,
            "density": 0.0,
        }
    col_frac = interference_mask.mean(axis=0)
    stripe = col_frac > 0.55
    widths = []
    run = 0
    for b in stripe:
        if b:
            run += 1
        elif run:
            widths.append(run)
            run = 0
    if run:
        widths.append(run)
    return {
        "stripe_count": float(stripe.sum()),
        "stripe_widths_median": float(np.median(widths)) if widths else 0.0,
        "affected_frequency_fraction": float(stripe.mean()) if stripe.size else 0.0,
        "persistence": float(col_frac[stripe].mean()) if stripe.any() else 0.0,
        "density": float(interference_mask.mean()),
    }
