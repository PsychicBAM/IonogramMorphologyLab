"""Multi-method image/structural similarity with registration checks."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

import numpy as np

from ionogram_morphology_lab.preprocessing.normalize import normalize_for_comparison
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame

SIMILARITY_METHODS = [
    "normalized_pixel_difference",
    "normalized_cross_correlation",
    "ssim",
    "edge_map_overlap",
    "trace_mask_overlap",
    "skeleton_overlap",
    "connected_component_comparison",
    "contour_similarity",
    "hausdorff_distance",
    "chamfer_distance",
    "horizontal_projection_similarity",
    "vertical_projection_similarity",
    "local_orientation_distribution_similarity",
    "temporal_sequence_similarity",
]


@dataclass
class SimilarityResult:
    status: str  # ok | not_comparable
    reason: str | None = None
    registration_confidence: float | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    label: str = "image_comparison_diagnostic_not_physical_proof"
    limitations: list[str] = field(
        default_factory=lambda: [
            "Similarity is an image-analysis diagnostic, not physical proof",
            "Never claim 'the same physical event'",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _axes_compatible(
    freq_a: np.ndarray | None,
    freq_b: np.ndarray | None,
    range_a: np.ndarray | None,
    range_b: np.ndarray | None,
) -> tuple[bool, str, float]:
    if freq_a is None or freq_b is None or range_a is None or range_b is None:
        # allow index-space comparison with reduced confidence
        return True, "index_space_fallback", 0.4
    if len(freq_a) != len(freq_b) or len(range_a) != len(range_b):
        return False, "axis_length_mismatch", 0.0
    if not np.allclose(freq_a, freq_b, rtol=1e-3, atol=1e-3):
        return False, "frequency_axis_mismatch", 0.0
    if not np.allclose(range_a, range_b, rtol=1e-3, atol=1e-3):
        return False, "range_axis_mismatch", 0.0
    return True, "axes_registered", 1.0


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.ravel()
    b = b.ravel()
    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _ssim_simple(a: np.ndarray, b: np.ndarray) -> float:
    try:
        from skimage.metrics import structural_similarity

        data_range = float(max(a.max() - a.min(), b.max() - b.min(), 1e-9))
        return float(structural_similarity(a, b, data_range=data_range))
    except Exception:  # noqa: BLE001
        # fallback correlation-like
        return _ncc(a, b)


def _mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union else 1.0


def _points(mask: np.ndarray) -> np.ndarray:
    return np.column_stack(np.nonzero(mask))


def _hausdorff(a: np.ndarray, b: np.ndarray) -> float:
    pa, pb = _points(a), _points(b)
    if pa.size == 0 or pb.size == 0:
        return float("inf")
    try:
        from scipy.spatial.distance import directed_hausdorff

        return float(max(directed_hausdorff(pa, pb)[0], directed_hausdorff(pb, pa)[0]))
    except Exception:  # noqa: BLE001
        return float("nan")


def _chamfer(a: np.ndarray, b: np.ndarray) -> float:
    pa, pb = _points(a), _points(b)
    if pa.size == 0 or pb.size == 0:
        return float("inf")
    from scipy.spatial import cKDTree

    da = cKDTree(pb).query(pa, k=1)[0].mean()
    db = cKDTree(pa).query(pb, k=1)[0].mean()
    return float((da + db) / 2)


def compare_ionograms(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    frequency_axis_a: np.ndarray | list[float] | None = None,
    frequency_axis_b: np.ndarray | list[float] | None = None,
    range_axis_a: np.ndarray | list[float] | None = None,
    range_axis_b: np.ndarray | list[float] | None = None,
) -> SimilarityResult:
    fa = np.asarray(frequency_axis_a, dtype=float) if frequency_axis_a is not None else None
    fb = np.asarray(frequency_axis_b, dtype=float) if frequency_axis_b is not None else None
    ra = np.asarray(range_axis_a, dtype=float) if range_axis_a is not None else None
    rb = np.asarray(range_axis_b, dtype=float) if range_axis_b is not None else None

    ok, reason, conf = _axes_compatible(fa, fb, ra, rb)
    if not ok:
        return SimilarityResult(status="not_comparable", reason=reason, registration_confidence=0.0)

    if frame_a.shape != frame_b.shape:
        return SimilarityResult(
            status="not_comparable",
            reason="shape_mismatch",
            registration_confidence=0.0,
        )

    na = normalize_for_comparison(frame_a).matrix
    nb = normalize_for_comparison(frame_b).matrix
    na = np.nan_to_num(na)
    nb = np.nan_to_num(nb)

    seg_a = segment_frame(frame_a)
    seg_b = segment_frame(frame_b)

    # edges
    try:
        from skimage.filters import sobel

        edge_a = sobel(na) > 0.1
        edge_b = sobel(nb) > 0.1
    except Exception:  # noqa: BLE001
        edge_a = seg_a.trace_mask
        edge_b = seg_b.trace_mask

    hp_a = seg_a.trace_mask.sum(axis=0).astype(float)
    hp_b = seg_b.trace_mask.sum(axis=0).astype(float)
    vp_a = seg_a.trace_mask.sum(axis=1).astype(float)
    vp_b = seg_b.trace_mask.sum(axis=1).astype(float)

    metrics = {
        "normalized_pixel_difference": float(np.mean(np.abs(na - nb))),
        "normalized_cross_correlation": _ncc(na, nb),
        "ssim": _ssim_simple(na, nb),
        "edge_map_overlap": _mask_iou(edge_a, edge_b),
        "trace_mask_overlap": _mask_iou(seg_a.trace_mask, seg_b.trace_mask),
        "skeleton_overlap": _mask_iou(seg_a.skeleton, seg_b.skeleton),
        "connected_component_comparison": float(
            1.0
            - abs(seg_a.component_map.max() - seg_b.component_map.max())
            / max(seg_a.component_map.max(), seg_b.component_map.max(), 1)
        ),
        "contour_similarity": _mask_iou(edge_a, edge_b),
        "hausdorff_distance": _hausdorff(seg_a.trace_mask, seg_b.trace_mask),
        "chamfer_distance": _chamfer(seg_a.trace_mask, seg_b.trace_mask),
        "horizontal_projection_similarity": _ncc(hp_a, hp_b),
        "vertical_projection_similarity": _ncc(vp_a, vp_b),
        "local_orientation_distribution_similarity": _ncc(
            np.diff(hp_a, prepend=hp_a[:1]), np.diff(hp_b, prepend=hp_b[:1])
        ),
        "temporal_sequence_similarity": float("nan"),
    }
    return SimilarityResult(
        status="ok",
        reason=reason,
        registration_confidence=conf,
        metrics=metrics,
    )
