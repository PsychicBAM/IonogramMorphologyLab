"""Physics-informed / interpretable morphology feature extraction."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

import numpy as np

from ionogram_morphology_lab.features.registry import FEATURE_REGISTRY
from ionogram_morphology_lab.segmentation.trace_interference import SegmentationResult, segment_frame


@dataclass
class FeatureVector:
    values: dict[str, float]
    parameters: dict[str, Any] = field(default_factory=dict)
    version: str = "iml1-0.2.0"
    limitations: list[str] = field(
        default_factory=lambda: [
            "Features are image-analysis measurements, not confirmed physical mechanisms",
            "Local ridge thickness is used for spread evidence; global row/column spans are diagnostic only",
            "No sunrise/sunset/solar variables used",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _entropy(prob: np.ndarray) -> float:
    p = prob[prob > 0]
    if p.size == 0:
        return 0.0
    p = p / p.sum()
    return float(-np.sum(p * np.log(p + 1e-12)))


def _span_widths_horizontal(mask: np.ndarray) -> np.ndarray:
    """Legacy global span widths (diagnostic / compatibility only)."""
    widths = []
    for row in mask:
        idx = np.where(row)[0]
        if idx.size:
            widths.append(float(idx.max() - idx.min() + 1))
    return np.asarray(widths, dtype=float) if widths else np.asarray([0.0])


def _span_widths_vertical(mask: np.ndarray) -> np.ndarray:
    widths = []
    for col in mask.T:
        idx = np.where(col)[0]
        if idx.size:
            widths.append(float(idx.max() - idx.min() + 1))
    return np.asarray(widths, dtype=float) if widths else np.asarray([0.0])


def _ridge_points(ridge_map: np.ndarray) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    h, w = ridge_map.shape
    for i in range(h):
        js = np.where(ridge_map[i] > 0)[0]
        if js.size:
            pts.append((i, int(js[0])))
    return pts


def _fwhm_1d(profile: np.ndarray, center: int) -> float:
    """Half-maximum width of the peak containing center on a 1-D amplitude profile."""
    if profile.size == 0 or center < 0 or center >= profile.size:
        return 0.0
    peak = float(profile[center])
    if not np.isfinite(peak) or peak <= 0:
        return 0.0
    half = 0.5 * peak
    lo = center
    while lo > 0 and float(profile[lo - 1]) >= half:
        lo -= 1
    hi = center
    while hi + 1 < profile.size and float(profile[hi + 1]) >= half:
        hi += 1
    return float(hi - lo + 1)


def _capped_run(mask_1d: np.ndarray, center: int, max_walk: int) -> float:
    if center < 0 or center >= mask_1d.size or not mask_1d[center]:
        return 0.0
    lo = hi = 0
    for d in range(1, max_walk + 1):
        if center - d < 0 or not mask_1d[center - d]:
            break
        lo += 1
    for d in range(1, max_walk + 1):
        if center + d >= mask_1d.size or not mask_1d[center + d]:
            break
        hi += 1
    return float(lo + hi + 1)


def _axis_halfwidths_at_ridge(
    frame: np.ndarray,
    mask: np.ndarray,
    ridge_pts: list[tuple[int, int]],
    interference_cols: np.ndarray | None = None,
    half_win: int = 12,
    band: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """EDT-radius-capped axis runs on the largest connected mask component.

    Walks along frequency/range from medial-axis samples, but never farther than
    the local EDT radius. Saturated equal walks on a thin tube are collapsed to
    half-iso on both axes (clean sloping ridge), while truly broad echoes retain
    larger one-sided or two-sided thickness.
    """
    del frame, half_win, band
    if not ridge_pts:
        return np.asarray([0.0]), np.asarray([0.0])
    h, w = mask.shape
    main = mask
    try:
        from skimage.measure import label

        lab = label(mask, connectivity=2)
        if lab.max() > 0:
            counts = np.bincount(lab.ravel())
            counts[0] = 0
            main = lab == int(np.argmax(counts))
    except Exception:  # noqa: BLE001
        main = mask
    try:
        from scipy.ndimage import distance_transform_edt

        edt = distance_transform_edt(main)
    except Exception:  # noqa: BLE001
        edt = np.ones(mask.shape, dtype=float)
    try:
        from skimage.morphology import skeletonize

        skel_pts = list(zip(*np.where(skeletonize(main))))
    except Exception:  # noqa: BLE001
        skel_pts = []
    sample_pts = [(int(i), int(j)) for i, j in skel_pts] or [
        (int(i), int(j)) for i, j in ridge_pts if main[i, j]
    ]
    # Global component aspect as a stable directional prior.
    ys, xs = np.where(main)
    if ys.size:
        comp_aspect = float((xs.max() - xs.min() + 1) / max(1, (ys.max() - ys.min() + 1)))
    else:
        comp_aspect = 1.0

    h_th: list[float] = []
    v_th: list[float] = []
    for i, j in sample_pts:
        if interference_cols is not None and j < interference_cols.size and interference_cols[j]:
            continue
        e0, e1 = max(0, i - 3), min(h, i + 4)
        f0, f1 = max(0, j - 3), min(w, j + 4)
        iso = float(2.0 * np.max(edt[e0:e1, f0:f1]))
        # Directional cue from limited walks (not whole-image spans).
        h_raw = _capped_run(main[i, :], j, max_walk=20)
        v_raw = _capped_run(main[:, j], i, max_walk=20)
        aniso = (h_raw - v_raw) / (h_raw + v_raw + 1e-6)
        # Aspect prior only when local walks are near-isotropic. Long sloping
        # traces always have a wide bbox; never use bbox aspect to override a
        # clear vertical (or horizontal) walk preference.
        if iso < 12.0 and abs(aniso) < 0.12:
            if comp_aspect >= 1.8:
                aniso = 0.20
            elif comp_aspect <= 0.55:
                aniso = -0.20
        # Thin medial tubes are not spread: keep both components below evidence thr.
        if iso < 8.0:
            h_th.append(0.4 * iso)
            v_th.append(0.4 * iso)
        elif aniso > 0.15:
            h_th.append(iso)
            v_th.append(min(iso * 0.45, max(0.0, iso * (1.0 - aniso))))
        elif aniso < -0.15:
            v_th.append(iso)
            h_th.append(min(iso * 0.45, max(0.0, iso * (1.0 + aniso))))
        else:
            h_th.append(iso)
            v_th.append(iso)
    if not h_th:
        return np.asarray([0.0]), np.asarray([0.0])
    return np.asarray(h_th, dtype=float), np.asarray(v_th, dtype=float)


def extract_features(
    frame: np.ndarray,
    segmentation: SegmentationResult | None = None,
    horiz_thr: float = 6.0,
    vert_thr: float = 6.0,
    half_win: int = 12,
) -> FeatureVector:
    """Extract interpretable features. Does not use solar/dawn/dusk context."""
    seg = segmentation or segment_frame(frame)
    mask = seg.trace_mask
    inter = seg.interference_mask
    h, w = mask.shape
    n = float(mask.size)

    # Diagnostic global spans (kept for provenance; not primary spread evidence).
    hw_span = _span_widths_horizontal(mask)
    vw_span = _span_widths_vertical(mask)

    ridge_pts = _ridge_points(seg.ridge_map)
    interference_cols = inter.any(axis=0) if inter.size else np.zeros(w, dtype=bool)
    local_h, local_v = _axis_halfwidths_at_ridge(
        frame, mask, ridge_pts, interference_cols=interference_cols, half_win=half_win
    )

    col_cov = float(mask.any(axis=0).mean()) if w else 0.0
    row_cov = float(mask.any(axis=1).mean()) if h else 0.0
    freq_proj = mask.sum(axis=0).astype(float)
    vert_proj = mask.sum(axis=1).astype(float)

    cols = np.where(mask.any(axis=0))[0]
    if cols.size >= 2:
        span = cols.max() - cols.min() + 1
        gap_fraction = 1.0 - (cols.size / span)
    else:
        gap_fraction = 1.0 if cols.size == 0 else 0.0

    cc = seg.component_map
    if cc.max() > 0:
        counts = np.bincount(cc.ravel())
        counts = counts[1:]
        component_count = int((counts > 0).sum())
        largest_frac = float(counts.max() / max(mask.sum(), 1))
    else:
        component_count = 0
        largest_frac = 0.0

    ridge_rows = [p[0] for p in ridge_pts]
    ridge_cols = [p[1] for p in ridge_pts]
    slopes = []
    for k in range(1, len(ridge_cols)):
        df = ridge_cols[k] - ridge_cols[k - 1]
        if df != 0:
            slopes.append((ridge_rows[k] - ridge_rows[k - 1]) / df)
    slope_std = float(np.std(slopes)) if slopes else 0.0

    branch_counts = []
    separations = []
    for j in range(w):
        idxs = np.where(mask[:, j])[0]
        if idxs.size == 0:
            continue
        splits = np.where(np.diff(idxs) > 3)[0]
        n_branches = len(splits) + 1
        branch_counts.append(n_branches)
        if n_branches >= 2:
            groups = np.split(idxs, splits + 1)
            means = [g.mean() for g in groups[:2]]
            separations.append(abs(means[0] - means[1]))
    parallel_branch_count = float(np.median(branch_counts)) if branch_counts else 0.0
    branch_separation = float(np.median(separations)) if separations else 0.0
    possible_ox = 0.0
    if parallel_branch_count >= 2 and branch_separation >= 3:
        possible_ox = min(1.0, 0.3 + 0.1 * min(branch_separation, 10) / 10)

    sat = 0.0
    finite = frame[np.isfinite(frame)]
    if finite.size:
        mx = float(finite.max())
        if mx > 0:
            sat = float(np.mean(finite >= 0.99 * mx))

    inter_pix = float(inter.sum())
    trace_pix = float(mask.sum())
    denom = inter_pix + trace_pix
    interference_dominance = inter_pix / denom if denom else 0.0

    # Primary spread evidence = local ridge thickness (not slope-induced global span).
    med_local_h = float(np.median(local_h))
    med_local_v = float(np.median(local_v))
    h_persist = float(np.mean(local_h > horiz_thr))
    v_persist = float(np.mean(local_v > vert_thr))
    # Absolute gates (used for mixed co-location) plus axis-dominance for single-axis labels.
    freq_abs = bool(med_local_h >= horiz_thr and h_persist >= 0.35)
    range_abs = bool(
        med_local_v >= vert_thr
        and v_persist >= 0.35
        and float(interference_cols.mean()) < 0.3
        and interference_dominance < 0.55
    )
    freq_evidence = float(freq_abs and med_local_h >= med_local_v * 1.15)
    range_evidence = float(range_abs and med_local_v >= med_local_h * 1.15)
    # Mixed absolute/co-location uses a stricter dual-axis threshold.
    mixed_thr = max(horiz_thr, vert_thr) + 2.0
    colocated = (
        float(np.mean((local_h >= mixed_thr) & (local_v >= mixed_thr))) if local_h.size else 0.0
    )
    freq_abs_f = float(med_local_h >= mixed_thr and h_persist >= 0.35)
    range_abs_f = float(
        med_local_v >= mixed_thr
        and v_persist >= 0.35
        and float(interference_cols.mean()) < 0.3
        and interference_dominance < 0.55
    )
    mixed_coverage = colocated
    mixed_score = float(np.sqrt(max(med_local_h, 0.0) * max(med_local_v, 0.0)) / 10.0)

    values = {
        "trace_pixel_fraction": trace_pix / n if n else 0.0,
        "trace_frequency_coverage": col_cov,
        "trace_virtual_height_coverage": row_cov,
        "largest_component_fraction": largest_frac,
        "component_count": float(component_count),
        "skeleton_length": float(seg.skeleton.sum()),
        "continuity_score": float(1.0 - gap_fraction),
        "gap_fraction": float(gap_fraction),
        "local_slope_distribution_std": slope_std,
        # Primary local-thickness features (also exposed under legacy width names used by rules).
        "median_horizontal_width": med_local_h,
        "max_horizontal_width": float(np.max(local_h)),
        "horizontal_width_variability": float(np.percentile(local_h, 75) - np.percentile(local_h, 25)),
        "frequency_projection_entropy": _entropy(freq_proj),
        "horizontal_broadening_persistence": h_persist,
        "median_vertical_width": med_local_v,
        "max_vertical_width": float(np.max(local_v)),
        "vertical_width_variability": float(np.percentile(local_v, 75) - np.percentile(local_v, 25)),
        "vertical_projection_entropy": _entropy(vert_proj),
        "vertical_broadening_persistence": v_persist,
        "mixed_width_score": mixed_score,
        "mixed_coverage": mixed_coverage,
        "frequency_evidence_passed": freq_evidence,
        "range_evidence_passed": range_evidence,
        "frequency_evidence_absolute": freq_abs_f,
        "range_evidence_absolute": range_abs_f,
        "colocated_spread_fraction": colocated,
        "global_span_horizontal_median": float(np.median(hw_span)),
        "global_span_vertical_median": float(np.median(vw_span)),
        "orientation_entropy": _entropy(np.abs(np.diff(ridge_cols)).astype(float) + 1)
        if len(ridge_cols) > 1
        else 0.0,
        "parallel_branch_count": parallel_branch_count,
        "branch_separation": branch_separation,
        "possible_ox_compatibility": possible_ox,
        "vertical_stripe_density": float(inter.any(axis=0).mean()) if w else 0.0,
        "full_height_stripe_count": float(np.sum(inter.mean(axis=0) >= 0.55)),
        "saturated_fraction": sat,
        "interference_dominance": interference_dominance,
        "temporal_persistence": float("nan"),
        "neighboring_frame_agreement": float("nan"),
    }
    values = {k: v for k, v in values.items() if k in FEATURE_REGISTRY}
    return FeatureVector(
        values=values,
        parameters={
            "horiz_thr": horiz_thr,
            "vert_thr": vert_thr,
            "half_win": half_win,
            "width_definition": "edt_split_by_local_axis_occupancy",
            "n_ridge_points": float(len(ridge_pts)),
        },
    )


def extract_temporal_features(masks: list[np.ndarray]) -> dict[str, float]:
    if len(masks) < 2:
        return {"temporal_persistence": float("nan"), "neighboring_frame_agreement": float("nan")}
    ious = []
    for a, b in zip(masks[:-1], masks[1:]):
        inter = np.logical_and(a, b).sum()
        union = np.logical_or(a, b).sum()
        ious.append(float(inter / union) if union else 1.0)
    return {
        "temporal_persistence": float(np.mean(ious)),
        "neighboring_frame_agreement": float(np.mean(ious)),
    }
