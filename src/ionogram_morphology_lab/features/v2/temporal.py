"""Temporal measurements from neighboring numeric frames — separate from single-frame."""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import CenterlineRecord, MeasuredFeature


def measure_temporal(
    current_trace: np.ndarray,
    current_interference: np.ndarray,
    current_centerlines: list[CenterlineRecord],
    current_h_width_med: float | None,
    current_v_width_med: float | None,
    neighbors: list[dict[str, Any]] | None,
    *,
    oversegmentation_suspected: bool = False,
) -> dict[str, MeasuredFeature]:
    """
    neighbors: list of dicts with keys:
      frame_index, trace_mask, interference_mask, centerlines,
      h_width_med, v_width_med, branch_count
    """
    feats: dict[str, MeasuredFeature] = {}
    if oversegmentation_suspected:
        for fid in (
            "v2_temporal_mask_overlap",
            "v2_temporal_centerline_displacement",
            "v2_temporal_width_persistence",
            "v2_temporal_interference_persistence",
            "v2_temporal_branch_persistence",
            "v2_temporal_event_class",
        ):
            # Branch persistence must abstain; other temporal metrics also abstain under overseg
            feats[fid] = MeasuredFeature(
                fid, None, unit="", valid=False,
                reason_invalid="oversegmentation_suspected",
                confidence_status="abstain",
            )
        return feats
    if not neighbors:
        for fid in (
            "v2_temporal_mask_overlap",
            "v2_temporal_centerline_displacement",
            "v2_temporal_width_persistence",
            "v2_temporal_interference_persistence",
            "v2_temporal_branch_persistence",
            "v2_temporal_event_class",
        ):
            feats[fid] = MeasuredFeature(
                fid, None, unit="", valid=False,
                reason_invalid="temporal_neighbors_unavailable",
                confidence_status="abstain",
                missing_prerequisites=["neighbor_frames"],
            )
        return feats

    overlaps = []
    displacements = []
    h_persist = []
    i_persist = []
    b_persist = []
    for nb in neighbors:
        tm = nb.get("trace_mask")
        if tm is not None and current_trace.any() and np.asarray(tm).any():
            a = current_trace.astype(bool)
            b = np.asarray(tm).astype(bool)
            inter = float((a & b).sum())
            union = float((a | b).sum()) or 1.0
            overlaps.append(inter / union)
        elif tm is not None:
            overlaps.append(0.0)

        # Centerline displacement (median row shift on common cols)
        cls = nb.get("centerlines") or []
        if current_centerlines and cls:
            a = {c: r for r, c in current_centerlines[0].points_rc}
            bmap = {c: r for r, c in cls[0].points_rc}
            common = set(a) & set(bmap)
            if common:
                displacements.append(float(np.median([abs(a[c] - bmap[c]) for c in common])))

        hw = nb.get("h_width_med")
        vw = nb.get("v_width_med")
        if current_h_width_med is not None and hw is not None:
            h_persist.append(1.0 - min(abs(current_h_width_med - float(hw)) / (current_h_width_med + 1e-9), 1.0))
        if current_v_width_med is not None and vw is not None:
            h_persist.append(1.0 - min(abs(current_v_width_med - float(vw)) / (current_v_width_med + 1e-9), 1.0))

        im = nb.get("interference_mask")
        if im is not None:
            a = current_interference.astype(bool)
            b = np.asarray(im).astype(bool)
            if a.any() or b.any():
                i_persist.append(float((a & b).sum()) / float((a | b).sum() or 1.0))
            else:
                i_persist.append(1.0)

        bc = nb.get("branch_count")
        cur_b = len(current_centerlines)
        if bc is not None:
            b_persist.append(1.0 if int(bc) == cur_b else 0.0)

    def _set(fid: str, values: list[float], unit: str) -> None:
        if not values:
            feats[fid] = MeasuredFeature(
                fid, None, unit=unit, valid=False,
                reason_invalid="insufficient_coverage", confidence_status="abstain",
            )
        else:
            feats[fid] = MeasuredFeature(
                fid, float(np.mean(values)), unit=unit, valid=True,
                uncertainty=float(np.std(values)) if len(values) > 1 else None,
                confidence_status="medium",
                metadata={"neighbor_count": len(neighbors), "separate_from_single_frame": True},
            )

    _set("v2_temporal_mask_overlap", overlaps, "fraction")
    _set("v2_temporal_centerline_displacement", displacements, "bins")
    _set("v2_temporal_width_persistence", h_persist, "score")
    _set("v2_temporal_interference_persistence", i_persist, "fraction")
    _set("v2_temporal_branch_persistence", b_persist, "score")

    # Event class heuristic (measurement label, not morphology)
    ov = float(np.mean(overlaps)) if overlaps else None
    event = "continuation"
    if ov is None:
        event_valid = False
        reason = "insufficient_coverage"
        event_val = None
    else:
        event_valid = True
        reason = ""
        if ov < 0.05 and current_trace.any():
            event = "sudden_appearance"
        elif ov < 0.05 and not current_trace.any():
            event = "sudden_disappearance"
        elif 0.05 <= ov < 0.35:
            event = "gradual_onset"
        elif ov >= 0.35:
            event = "continuation"
        # Isolated artifact: current has tiny mask, neighbors empty-ish
        if current_trace.any() and current_trace.mean() < 0.002 and ov < 0.1:
            event = "likely_isolated_artifact"
        event_val = event

    feats["v2_temporal_event_class"] = MeasuredFeature(
        "v2_temporal_event_class", event_val, unit="categorical",
        valid=event_valid, reason_invalid=reason,
        confidence_status="low" if event_valid else "abstain",
        metadata={"note": "does_not_borrow_neighbor_classification"},
    )
    return feats
