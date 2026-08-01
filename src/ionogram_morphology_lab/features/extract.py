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
    version: str = "iml1-0.1.0"
    limitations: list[str] = field(
        default_factory=lambda: [
            "Features are image-analysis measurements, not confirmed physical mechanisms",
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


def _widths_horizontal(mask: np.ndarray) -> np.ndarray:
    widths = []
    for row in mask:
        idx = np.where(row)[0]
        if idx.size:
            widths.append(float(idx.max() - idx.min() + 1))
    return np.asarray(widths, dtype=float) if widths else np.asarray([0.0])


def _widths_vertical(mask: np.ndarray) -> np.ndarray:
    widths = []
    for col in mask.T:
        idx = np.where(col)[0]
        if idx.size:
            widths.append(float(idx.max() - idx.min() + 1))
    return np.asarray(widths, dtype=float) if widths else np.asarray([0.0])


def extract_features(
    frame: np.ndarray,
    segmentation: SegmentationResult | None = None,
    horiz_thr: float = 4.0,
    vert_thr: float = 6.0,
) -> FeatureVector:
    """Extract interpretable features. Does not use solar/dawn/dusk context."""
    seg = segmentation or segment_frame(frame)
    mask = seg.trace_mask
    inter = seg.interference_mask
    h, w = mask.shape
    n = float(mask.size)

    hw = _widths_horizontal(mask)
    vw = _widths_vertical(mask)

    col_cov = float(mask.any(axis=0).mean()) if w else 0.0
    row_cov = float(mask.any(axis=1).mean()) if h else 0.0
    freq_proj = mask.sum(axis=0).astype(float)
    vert_proj = mask.sum(axis=1).astype(float)

    # gaps along frequency span
    cols = np.where(mask.any(axis=0))[0]
    if cols.size >= 2:
        span = cols.max() - cols.min() + 1
        gap_fraction = 1.0 - (cols.size / span)
    else:
        gap_fraction = 1.0 if cols.size == 0 else 0.0

    cc = seg.component_map
    if cc.max() > 0:
        counts = np.bincount(cc.ravel())
        counts = counts[1:]  # drop background
        component_count = int((counts > 0).sum())
        largest_frac = float(counts.max() / max(mask.sum(), 1))
    else:
        component_count = 0
        largest_frac = 0.0

    # ridge slopes
    ridge_rows = []
    ridge_cols = []
    for i in range(h):
        js = np.where(seg.ridge_map[i] > 0)[0]
        if js.size:
            ridge_rows.append(i)
            ridge_cols.append(int(js[0]))
    slopes = []
    for k in range(1, len(ridge_cols)):
        df = ridge_cols[k] - ridge_cols[k - 1]
        if df != 0:
            slopes.append((ridge_rows[k] - ridge_rows[k - 1]) / df)
    slope_std = float(np.std(slopes)) if slopes else 0.0

    # branch estimate: for each freq col, count distinct local maxima rows in bright
    branch_counts = []
    separations = []
    for j in range(w):
        col = frame[:, j] if np.isfinite(frame[:, j]).any() else np.zeros(h)
        # simple: peaks in mask column
        idxs = np.where(mask[:, j])[0]
        if idxs.size == 0:
            continue
        # cluster gaps
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
        # clean-ish double branch heuristic
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

    mixed_score = float(np.sqrt(max(np.median(hw), 0) * max(np.median(vw), 0)) / 10.0)
    mixed_cov = float(
        ((hw.mean() if hw.size else 0) > horiz_thr) and ((vw.mean() if vw.size else 0) > vert_thr)
    )

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
        "median_horizontal_width": float(np.median(hw)),
        "max_horizontal_width": float(np.max(hw)),
        "horizontal_width_variability": float(np.percentile(hw, 75) - np.percentile(hw, 25)),
        "frequency_projection_entropy": _entropy(freq_proj),
        "horizontal_broadening_persistence": float(np.mean(hw > horiz_thr)),
        "median_vertical_width": float(np.median(vw)),
        "max_vertical_width": float(np.max(vw)),
        "vertical_width_variability": float(np.percentile(vw, 75) - np.percentile(vw, 25)),
        "vertical_projection_entropy": _entropy(vert_proj),
        "vertical_broadening_persistence": float(np.mean(vw > vert_thr)),
        "mixed_width_score": mixed_score,
        "mixed_coverage": mixed_cov,
        "orientation_entropy": _entropy(np.abs(np.diff(ridge_cols)).astype(float) + 1)
        if len(ridge_cols) > 1
        else 0.0,
        "parallel_branch_count": parallel_branch_count,
        "branch_separation": branch_separation,
        "possible_ox_compatibility": possible_ox,
        "vertical_stripe_density": float(inter.any(axis=0).mean()) if w else 0.0,
        "full_height_stripe_count": float(inter.mean(axis=0).sum() >= 0)  # placeholder fixed below
        ,
        "saturated_fraction": sat,
        "interference_dominance": interference_dominance,
        "temporal_persistence": float("nan"),
        "neighboring_frame_agreement": float("nan"),
    }
    # fix full_height_stripe_count
    values["full_height_stripe_count"] = float(np.sum(inter.mean(axis=0) >= 0.55))

    # Only emit registered features
    values = {k: v for k, v in values.items() if k in FEATURE_REGISTRY}
    return FeatureVector(
        values=values,
        parameters={"horiz_thr": horiz_thr, "vert_thr": vert_thr},
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
