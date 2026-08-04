"""Explainable numeric trace extraction — candidates, interference, floor, centerlines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import ndimage

from ionogram_morphology_lab.features.v2.consolidation import (
    PLAUSIBILITY_WARNING_ABOVE,
    consolidate_centerlines,
    evaluate_oversegmentation,
)
from ionogram_morphology_lab.features.v2.types import CenterlineRecord, MeasuredFeature

# Project heuristics (not physical morphology thresholds)
FLOOR_BAND_FRAC = 1 / 12
FLOOR_DOMINATED_FRAC = 0.55
FLOOR_CONTINUATION_MIN_FRAC = 0.20
FLOOR_ABOVE_AMP_RATIO = 0.35


@dataclass
class TraceExtractionResult:
    masks: dict[str, np.ndarray]
    centerlines: list[CenterlineRecord]
    features: dict[str, MeasuredFeature]
    pixel_reasons: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    raw_centerlines: list[CenterlineRecord] = field(default_factory=list)
    component_decisions: dict[str, Any] = field(default_factory=dict)
    oversegmentation_suspected: bool = False
    branch_records: list[dict[str, Any]] = field(default_factory=list)


def extract_trace(
    raw: np.ndarray,
    score: np.ndarray,
    quality_status: str,
) -> TraceExtractionResult:
    """Multi-stage explainable trace extraction (not a single global threshold)."""
    h, w = raw.shape
    feats: dict[str, MeasuredFeature] = {}
    notes: list[str] = []

    empty = {
        "trace_candidate_before_exclusion": np.zeros((h, w), dtype=bool),
        "trace_candidate": np.zeros((h, w), dtype=bool),
        "trace_accepted": np.zeros((h, w), dtype=bool),
        "interference": np.zeros((h, w), dtype=bool),
        "background": np.ones((h, w), dtype=bool),
        "uncertain": np.zeros((h, w), dtype=bool),
        "excluded": np.zeros((h, w), dtype=bool),
        "branch_labels": np.zeros((h, w), dtype=np.int32),
        "centerlines_before": np.zeros((h, w), dtype=bool),
        "centerlines_after": np.zeros((h, w), dtype=bool),
        "floor_clutter": np.zeros((h, w), dtype=bool),
        "impulses": np.zeros((h, w), dtype=bool),
        "plausible_pre_exclusion": np.zeros((h, w), dtype=bool),
    }

    count_ids = (
        "v2_trace_pixel_fraction",
        "v2_centerline_count",
        "v2_total_connected_component_count",
        "v2_preconsolidation_centerline_count",
        "v2_floor_rejected_component_count",
        "v2_accepted_nonfloor_trace_fraction",
        "v2_preexclusion_floor_overlap_fraction",
        "v2_floor_candidate_removed_fraction",
        "v2_nonfloor_candidate_retained_fraction",
        "v2_accepted_support_above_floor_fraction",
        "v2_unresolved_floor_conflict_fraction",
        "v2_consolidated_branch_count",
        "v2_rejected_component_count",
        "v2_consolidation_count",
        "v2_fragmentation_score",
        "v2_oversegmentation_suspected",
        "v2_raw_component_count",  # alias of preconsolidation_centerline_count
    )

    if quality_status == "not_assessable":
        for fid in count_ids:
            feats[fid] = MeasuredFeature(
                fid, None, unit="", valid=False,
                reason_invalid="trace_not_found", confidence_status="abstain",
                missing_prerequisites=["assessable_frame"],
            )
        return TraceExtractionResult(
            empty, [], feats, notes=["quality_not_assessable"],
            component_decisions={
                "total_connected_component_count": 0,
                "preconsolidation_centerline_count": 0,
                "floor_rejected_component_count": 0,
                "consolidated_branch_count": 0,
                "rejected_component_count": 0,
                "consolidation_count": 0,
                "fragmentation_score": 0.0,
                "oversegmentation_suspected": False,
                "decisions": [],
                "notes": ["quality_not_assessable"],
            },
        )

    x = score.astype(np.float64)
    col_med = np.median(x, axis=0)
    col_mad = np.median(np.abs(x - col_med), axis=0) + 1e-9
    snr = (x - col_med) / (1.4826 * col_mad)

    interference = _detect_vertical_interference(snr, raw=raw)
    floor = _detect_floor_clutter(snr)
    impulses = _detect_impulses(snr)

    thr = 2.5
    # Plausible elevated support BEFORE excluding interference/floor/impulses
    plausible = snr > thr
    dilated = ndimage.binary_dilation(plausible, iterations=1)
    plausible = plausible | ((snr > 1.5) & dilated)
    plausible_pre_exclusion = plausible.copy()

    # When interference is dominant, do not seed new candidates inside stripes
    # Working candidate: remove interference and impulses, but keep floor for
    # per-component floor analysis (not a silent hard height cutoff alone).
    working = plausible & (~interference) & (~impulses)
    interf_frac = float(interference.mean()) if interference.size else 0.0
    labeled, nlab = ndimage.label(working)

    uncertain = np.zeros_like(working)
    accepted_pre = np.zeros_like(working)
    preconsol_centerlines: list[CenterlineRecord] = []
    prior_rejections: list[dict[str, Any]] = []
    floor_rejected = 0
    kept = 0
    component_floor_meta: list[dict[str, Any]] = []

    for lab in range(1, nlab + 1):
        comp = labeled == lab
        area = int(comp.sum())
        cols = np.where(comp.any(axis=0))[0]
        rows = np.where(comp.any(axis=1))[0]
        floor_overlap = float((comp & floor).sum() / max(area, 1))
        above_floor = comp & (~floor)
        above_frac = float(above_floor.sum() / max(area, 1))
        if above_floor.any():
            amp_above = float(np.median(snr[above_floor]))
            amp_floor = float(np.median(snr[comp & floor])) if (comp & floor).any() else 0.0
            ridge_above = amp_above >= max(thr * FLOOR_ABOVE_AMP_RATIO, 1.0)
        else:
            amp_above = 0.0
            amp_floor = float(np.median(snr[comp])) if area else 0.0
            ridge_above = False
        floor_metrics = {
            "floor_overlap_fraction": floor_overlap,
            "support_inside_floor_fraction": floor_overlap,
            "continuation_above_floor_fraction": above_frac,
            "amplitude_above_floor": amp_above,
            "amplitude_in_floor": amp_floor,
            "ridge_evidence_above_floor": ridge_above,
            "area": area,
        }
        component_floor_meta.append({"id": lab, **floor_metrics})

        if area < 8 or cols.size < 3:
            uncertain |= comp
            prior_rejections.append({"id": lab, "accepted": False, "reason": "too_small", **floor_metrics})
            continue
        span_c = int(cols.max() - cols.min() + 1)
        span_r = int(rows.max() - rows.min() + 1)
        aspect = span_c / max(span_r, 1)
        if span_c < 5 and aspect < 1.2:
            uncertain |= comp
            prior_rejections.append({"id": lab, "accepted": False, "reason": "not_ridge_like", **floor_metrics})
            continue

        # Floor-dominated without adequate continuation / ridge above floor
        floor_dominated = floor_overlap >= FLOOR_DOMINATED_FRAC and (
            above_frac < FLOOR_CONTINUATION_MIN_FRAC or not ridge_above
        )
        if floor_dominated:
            uncertain |= comp
            floor_rejected += 1
            prior_rejections.append(
                {"id": lab, "accepted": False, "reason": "floor_component", **floor_metrics}
            )
            continue

        # Strip floor pixels from accepted support when component continues above
        keep_mask = above_floor if above_floor.any() else comp
        if not keep_mask.any():
            floor_rejected += 1
            prior_rejections.append(
                {"id": lab, "accepted": False, "reason": "floor_component", **floor_metrics}
            )
            continue

        kept += 1
        accepted_pre |= keep_mask
        cl = _centerline_from_component(
            keep_mask, snr, branch_id=kept, component_id=lab, interference=interference, floor=floor
        )
        cl.floor_overlap_fraction = floor_overlap
        preconsol_centerlines.append(cl)

    # Candidate after exclusion: non-floor working pixels that are not uncertain-only floor junk
    candidate = working & (~floor)
    # Retain accepted nonfloor even if dilation brought weak edges
    candidate = candidate | accepted_pre

    cons = consolidate_centerlines(
        preconsol_centerlines,
        snr=snr,
        interference=interference,
        shape=(h, w),
        prior_rejections=prior_rejections,
        floor_mask=floor,
    )

    from ionogram_morphology_lab.features.v2.consolidation import ComponentDecision

    centerlines = cons.consolidated_centerlines
    # Drop consolidated branches that are still floor-dominated
    kept_cls: list[CenterlineRecord] = []
    branch_labels = np.zeros((h, w), dtype=np.int32)
    floor_branch_count = 0
    for cl in centerlines:
        pts_floor = 0
        for r, c in cl.points_rc:
            if 0 <= r < h and 0 <= c < w and floor[r, c]:
                pts_floor += 1
        frac = pts_floor / max(cl.point_count, 1)
        med_r = float(np.median([r for r, _ in cl.points_rc])) if cl.points_rc else 0.0
        # Reject only when floor-dominated (overlap), not by height cutoff alone
        if frac >= FLOOR_DOMINATED_FRAC:
            floor_branch_count += 1
            floor_rejected += 1
            cons.decisions.append(
                ComponentDecision(
                    component_id=cl.component_id,
                    decision="rejected",
                    reasons=["floor_component"],
                    metrics={"floor_overlap_fraction": frac, "median_row": med_r, "stage": "post_consolidation"},
                )
            )
            continue
        kept_cls.append(cl)
    centerlines = kept_cls
    # Dominant full-height interference: no confident ionospheric trace
    stripe_dom = float((interference.mean(axis=0) > 0.55).mean()) if w else 0.0
    if stripe_dom >= 0.18:
        # Wide full-height clutter: abstain from confident branches (measurement retained as empty)
        for cl in centerlines:
            cons.decisions.append(
                ComponentDecision(
                    component_id=cl.component_id,
                    decision="rejected",
                    reasons=["full_height_interference_clutter"],
                    metrics={"stripe_dom": stripe_dom},
                )
            )
        centerlines = []
        notes.append("interference_dominant_trace_abstain")

    # Re-evaluate overseg after floor-branch purge / interference abstain
    overseg, overseg_meta = evaluate_oversegmentation(
        cons,
        accepted=accepted_pre & (~floor),
        floor=floor,
        centerlines=centerlines,
        shape=(h, w),
    )
    if stripe_dom >= 0.18:
        overseg = True
        overseg_meta = {
            **overseg_meta,
            "suspected": True,
            "reasons": list(overseg_meta.get("reasons", [])) + ["full_height_interference_clutter"],
            "stripe_dominated_fraction": stripe_dom,
        }
    cons.oversegmentation_suspected = overseg
    for bid, cl in enumerate(centerlines, start=1):
        cl.branch_id = bid
        for r, c in cl.points_rc:
            if 0 <= r < h and 0 <= c < w and not floor[r, c]:
                branch_labels[r, c] = bid
                for dr in (-1, 0, 1):
                    rr = r + dr
                    if 0 <= rr < h and branch_labels[rr, c] == 0 and not floor[rr, c]:
                        branch_labels[rr, c] = bid

    accepted = (branch_labels > 0) & (~floor)
    if accepted.any():
        accepted = ndimage.binary_dilation(accepted, iterations=1) & candidate & (~floor)
        if not accepted.any():
            accepted = branch_labels > 0

    before_mask = np.zeros((h, w), dtype=bool)
    for cl in preconsol_centerlines:
        for r, c in cl.points_rc:
            if 0 <= r < h and 0 <= c < w:
                before_mask[r, c] = True
    after_mask = np.zeros((h, w), dtype=bool)
    for cl in centerlines:
        for r, c in cl.points_rc:
            if 0 <= r < h and 0 <= c < w:
                after_mask[r, c] = True

    background = ~(plausible | interference | impulses)
    excluded = interference | floor | impulses

    # Postcondition check only — accepted is constructed as non-floor; do not treat as quality evidence
    nonfloor_frac = float((accepted & ~floor).sum() / max(int(accepted.sum()), 1)) if accepted.any() else 0.0
    floor_in_accepted = float((accepted & floor).sum() / max(int(accepted.sum()), 1)) if accepted.any() else 0.0

    pre_n = max(int(plausible_pre_exclusion.sum()), 1)
    pre_floor_ov = float((plausible_pre_exclusion & floor).sum() / pre_n) if plausible_pre_exclusion.any() else 0.0
    cand_before_floor = plausible_pre_exclusion
    cand_nonfloor = cand_before_floor & (~floor)
    removed = float((cand_before_floor & floor).sum() / max(int(cand_before_floor.sum()), 1)) if cand_before_floor.any() else 0.0
    retained = float(cand_nonfloor.sum() / max(int(cand_before_floor.sum()), 1)) if cand_before_floor.any() else 0.0
    above_floor_support = float((accepted & (~floor)).sum() / max(int(accepted.sum()), 1)) if accepted.any() else 0.0
    # Unresolved: uncertain pixels that still overlap floor after rejection
    unresolved = float((uncertain & floor).sum() / max(int((uncertain | floor).sum()), 1)) if (uncertain | floor).any() else 0.0

    # Potential trace/interference overlap on pre-exclusion plausible mask
    pot_overlap = float((plausible_pre_exclusion & interference).sum() / max(int(plausible_pre_exclusion.sum()), 1)) if plausible_pre_exclusion.any() else 0.0

    feats["v2_total_connected_component_count"] = MeasuredFeature(
        "v2_total_connected_component_count", float(nlab), unit="count", valid=True, confidence_status="high",
    )
    feats["v2_preconsolidation_centerline_count"] = MeasuredFeature(
        "v2_preconsolidation_centerline_count", float(len(preconsol_centerlines)), unit="count",
        valid=True, confidence_status="high",
        metadata={"note": "ridge-like components accepted before consolidation (not all connected components)"},
    )
    # Backward-compatible alias with corrected meaning documented in metadata
    feats["v2_raw_component_count"] = MeasuredFeature(
        "v2_raw_component_count", float(len(preconsol_centerlines)), unit="count",
        valid=True, confidence_status="high",
        metadata={"alias_of": "v2_preconsolidation_centerline_count"},
    )
    feats["v2_floor_rejected_component_count"] = MeasuredFeature(
        "v2_floor_rejected_component_count", float(floor_rejected), unit="count",
        valid=True, confidence_status="high",
    )
    feats["v2_accepted_nonfloor_trace_fraction"] = MeasuredFeature(
        "v2_accepted_nonfloor_trace_fraction", nonfloor_frac, unit="fraction",
        valid=bool(accepted.any()),
        reason_invalid="" if accepted.any() else "trace_not_found",
        confidence_status="low" if accepted.any() else "abstain",
        metadata={
            "floor_pixels_in_accepted_fraction": floor_in_accepted,
            "role": "postcondition_check_only",
            "note": "Usually ~1.0 by construction after floor exclusion — not extraction-quality evidence",
        },
    )
    feats["v2_preexclusion_floor_overlap_fraction"] = MeasuredFeature(
        "v2_preexclusion_floor_overlap_fraction", pre_floor_ov, unit="fraction",
        valid=bool(plausible_pre_exclusion.any()),
        reason_invalid="" if plausible_pre_exclusion.any() else "no_preexclusion_candidate",
        confidence_status="medium" if plausible_pre_exclusion.any() else "abstain",
    )
    feats["v2_floor_candidate_removed_fraction"] = MeasuredFeature(
        "v2_floor_candidate_removed_fraction", removed, unit="fraction",
        valid=bool(cand_before_floor.any()),
        reason_invalid="" if cand_before_floor.any() else "no_candidate",
        confidence_status="medium" if cand_before_floor.any() else "abstain",
    )
    feats["v2_nonfloor_candidate_retained_fraction"] = MeasuredFeature(
        "v2_nonfloor_candidate_retained_fraction", retained, unit="fraction",
        valid=bool(cand_before_floor.any()),
        reason_invalid="" if cand_before_floor.any() else "no_candidate",
        confidence_status="medium" if cand_before_floor.any() else "abstain",
    )
    feats["v2_accepted_support_above_floor_fraction"] = MeasuredFeature(
        "v2_accepted_support_above_floor_fraction", above_floor_support, unit="fraction",
        valid=bool(accepted.any()),
        reason_invalid="" if accepted.any() else "trace_not_found",
        confidence_status="medium" if accepted.any() else "abstain",
    )
    feats["v2_unresolved_floor_conflict_fraction"] = MeasuredFeature(
        "v2_unresolved_floor_conflict_fraction", unresolved, unit="fraction",
        valid=True, confidence_status="medium",
    )
    feats["v2_consolidated_branch_count"] = MeasuredFeature(
        "v2_consolidated_branch_count", float(len(centerlines)), unit="count",
        valid=True, confidence_status="medium",
        metadata={
            "plausibility_warning_above": PLAUSIBILITY_WARNING_ABOVE,
            "plausibility_warning": len(centerlines) > PLAUSIBILITY_WARNING_ABOVE,
            "floor_branch_rejected": floor_branch_count,
        },
    )
    feats["v2_rejected_component_count"] = MeasuredFeature(
        "v2_rejected_component_count", float(cons.rejected_component_count + floor_rejected),
        unit="count", valid=True, confidence_status="high",
    )
    feats["v2_consolidation_count"] = MeasuredFeature(
        "v2_consolidation_count", float(cons.consolidation_count), unit="count",
        valid=True, confidence_status="high",
    )
    frag = float(len(preconsol_centerlines) / max(len(centerlines), 1)) if preconsol_centerlines else 0.0
    feats["v2_fragmentation_score"] = MeasuredFeature(
        "v2_fragmentation_score", frag, unit="ratio", valid=True, confidence_status="medium",
    )
    feats["v2_oversegmentation_suspected"] = MeasuredFeature(
        "v2_oversegmentation_suspected", float(1.0 if overseg else 0.0), unit="flag",
        valid=True, confidence_status="medium", metadata=overseg_meta,
    )
    # potential overlap is finalized in measure_interference (pre-exclusion)
    _ = pot_overlap

    branch_records: list[dict[str, Any]] = []
    if not centerlines:
        feats["v2_trace_pixel_fraction"] = MeasuredFeature(
            "v2_trace_pixel_fraction", None, unit="fraction", valid=False,
            reason_invalid="trace_not_found", confidence_status="abstain",
        )
        feats["v2_centerline_count"] = MeasuredFeature(
            "v2_centerline_count", 0.0, unit="count", valid=True, confidence_status="high",
            metadata={"plausibility_warning_above": PLAUSIBILITY_WARNING_ABOVE},
        )
        notes.append("no_accepted_trace")
    else:
        cont = float(np.mean([c.continuity for c in centerlines]))
        cov = float(accepted.mean())
        conf_status = "abstain" if overseg else "medium"
        feats["v2_trace_pixel_fraction"] = MeasuredFeature(
            "v2_trace_pixel_fraction", cov, unit="fraction",
            valid=not overseg,
            reason_invalid="oversegmentation_suspected" if overseg else "",
            uncertainty=0.05,
            confidence_status=conf_status if quality_status == "assessable" else "low",
        )
        feats["v2_centerline_count"] = MeasuredFeature(
            "v2_centerline_count", float(len(centerlines)), unit="count", valid=True,
            confidence_status="low" if overseg else "medium",
            metadata={
                "preconsolidation_centerline_count": len(preconsol_centerlines),
                "oversegmentation_suspected": overseg,
                "open_ended_count": True,
                "plausibility_warning_above": PLAUSIBILITY_WARNING_ABOVE,
            },
        )
        feats["v2_trace_continuity"] = MeasuredFeature(
            "v2_trace_continuity", cont, unit="fraction",
            valid=not overseg,
            reason_invalid="oversegmentation_suspected" if overseg else "",
            confidence_status=conf_status,
        )
        for cl in centerlines:
            branch_records.append(
                {
                    "branch_id": cl.branch_id,
                    "component_id": cl.component_id,
                    "member_component_ids": list(cl.member_component_ids),
                    "frequency_span_bins": list(cl.frequency_span_bins),
                    "height_span_bins": list(cl.height_span_bins),
                    "frequency_span_width": int(cl.frequency_span_bins[1] - cl.frequency_span_bins[0] + 1),
                    "height_span_width": int(cl.height_span_bins[1] - cl.height_span_bins[0] + 1),
                    "point_count": cl.point_count,
                    "continuity": cl.continuity,
                    "gap_fraction": cl.gap_fraction,
                    "slope": cl.slope,
                    "curvature": cl.curvature,
                    "interference_overlap": cl.interference_overlap,
                    "floor_overlap_fraction": getattr(cl, "floor_overlap_fraction", 0.0),
                    "component_confidence": cl.component_confidence,
                    "quality_status": cl.quality_status,
                    "valid": not overseg,
                    "reason_invalid": "oversegmentation_suspected" if overseg else "",
                }
            )

    notes.extend(cons.notes)
    ser = cons.to_serializable()
    ser.update(
        {
            "total_connected_component_count": nlab,
            "preconsolidation_centerline_count": len(preconsol_centerlines),
            "floor_rejected_component_count": floor_rejected,
            "component_floor_metrics": component_floor_meta,
            "oversegmentation_evidence": overseg_meta,
            "accepted_nonfloor_trace_fraction": nonfloor_frac,
        }
    )

    masks = {
        "trace_candidate_before_exclusion": plausible_pre_exclusion,
        "plausible_pre_exclusion": plausible_pre_exclusion,
        "trace_candidate": candidate,
        "trace_accepted": accepted,
        "interference": interference,
        "background": background,
        "uncertain": uncertain,
        "excluded": excluded,
        "branch_labels": branch_labels,
        "floor_clutter": floor,
        "impulses": impulses,
        "centerlines_before": before_mask,
        "centerlines_after": after_mask,
    }
    return TraceExtractionResult(
        masks=masks,
        centerlines=centerlines,
        features=feats,
        pixel_reasons={"snr_threshold": thr, "floor_heuristics": {
            "FLOOR_BAND_FRAC": FLOOR_BAND_FRAC,
            "FLOOR_DOMINATED_FRAC": FLOOR_DOMINATED_FRAC,
            "FLOOR_CONTINUATION_MIN_FRAC": FLOOR_CONTINUATION_MIN_FRAC,
        }},
        notes=notes,
        raw_centerlines=preconsol_centerlines,
        component_decisions=ser,
        oversegmentation_suspected=overseg,
        branch_records=branch_records,
    )


def _detect_vertical_interference(snr: np.ndarray, raw: np.ndarray | None = None) -> np.ndarray:
    h, w = snr.shape
    thr = 2.0
    bright = snr > thr
    col_frac = bright.mean(axis=0)
    stripe_cols = col_frac > 0.55

    if raw is not None:
        r = np.asarray(raw, dtype=float)
        g_med = float(np.median(r))
        g_p90 = float(np.percentile(r, 90)) if r.size else g_med
        col_mean = r.mean(axis=0)
        col_std = r.std(axis=0)
        thr_bright = max(g_p90, g_med + 1e-6)
        const_bright = (col_mean >= thr_bright) & (col_std <= np.maximum(0.15 * col_mean, 1e-6))
        high_frac = (r > (g_med + 0.5 * max(g_p90 - g_med, 1.0))).mean(axis=0)
        const_bright = const_bright | ((high_frac > 0.7) & (col_mean > g_med + 1e-6))
        stripe_cols = np.asarray(stripe_cols) | const_bright

    interference = np.zeros((h, w), dtype=bool)
    if stripe_cols.any():
        interference[:, stripe_cols] = True
        for j in np.where(stripe_cols)[0]:
            for dj in (-1, 1):
                jj = j + dj
                if 0 <= jj < w and (col_frac[jj] > 0.35 or (raw is not None and bool(stripe_cols[jj]))):
                    interference[:, jj] = True
    return interference


def _detect_floor_clutter(snr: np.ndarray) -> np.ndarray:
    """Lower-edge clutter mask — project heuristic band, not a morphology rule."""
    h, w = snr.shape
    floor_h = max(2, int(round(h * FLOOR_BAND_FRAC)))
    band = snr[:floor_h, :]
    thr = 1.5
    mask = np.zeros_like(snr, dtype=bool)
    # Mark elevated lower-edge pixels; do not require global band density
    mask[:floor_h, :] = band > thr
    return mask


def _detect_impulses(snr: np.ndarray) -> np.ndarray:
    bright = snr > 4.0
    labeled, n = ndimage.label(bright)
    impulses = np.zeros_like(bright)
    for lab in range(1, n + 1):
        comp = labeled == lab
        if comp.sum() <= 4:
            dil = ndimage.binary_dilation(comp, iterations=2)
            if (bright & dil & ~comp).sum() < 3:
                impulses |= comp
    return impulses


def _centerline_from_component(
    comp: np.ndarray,
    snr: np.ndarray,
    *,
    branch_id: int,
    component_id: int,
    interference: np.ndarray,
    floor: np.ndarray | None = None,
) -> CenterlineRecord:
    points: list[tuple[int, int]] = []
    cols = np.where(comp.any(axis=0))[0]
    gaps = 0
    prev = None
    for c in cols:
        rows = np.where(comp[:, c])[0]
        if rows.size == 0:
            gaps += 1
            continue
        weights = np.clip(snr[rows, c], 0, None) + 1e-6
        r = int(np.round(np.average(rows, weights=weights)))
        points.append((r, int(c)))
        if prev is not None and int(c) - prev > 1:
            gaps += int(c) - prev - 1
        prev = int(c)

    if not points:
        return CenterlineRecord(
            branch_id=branch_id, component_id=component_id, points_rc=[],
            frequency_span_bins=(0, 0), height_span_bins=(0, 0), point_count=0,
            continuity=0.0, gap_fraction=1.0, slope=0.0, curvature=0.0,
            interference_overlap=0.0, quality_status="invalid",
            member_component_ids=[component_id], component_confidence=0.0,
        )

    rs = np.array([p[0] for p in points], dtype=float)
    cs = np.array([p[1] for p in points], dtype=float)
    span_c = (int(cs.min()), int(cs.max()))
    span_r = (int(rs.min()), int(rs.max()))
    expected = max(int(cs.max() - cs.min()) + 1, 1)
    continuity = len(points) / expected
    gap_fraction = gaps / expected
    slope = float(np.polyfit(cs, rs, 1)[0]) if len(points) >= 2 else 0.0
    curvature = float(np.mean(np.abs(np.diff(np.diff(rs))))) if len(points) >= 3 else 0.0
    ov = float(np.mean([interference[r, c] for r, c in points]))
    floor_ov = 0.0
    if floor is not None:
        floor_ov = float(np.mean([floor[r, c] for r, c in points]))
    q = "good" if continuity > 0.7 and ov < 0.2 else ("partial" if continuity > 0.4 else "poor")
    amps = [float(snr[r, c]) for r, c in points]
    amp_score = float(np.clip(np.median(amps) / 5.0, 0, 1)) if amps else 0.0
    conf = float(
        0.25 * amp_score
        + 0.25 * np.clip(continuity, 0, 1)
        + 0.2 * np.clip(1.0 - gap_fraction, 0, 1)
        + 0.15 * np.clip(1.0 - ov, 0, 1)
        + 0.15 * np.clip(len(points) / 40.0, 0, 1)
    )
    rec = CenterlineRecord(
        branch_id=branch_id,
        component_id=component_id,
        points_rc=points,
        frequency_span_bins=span_c,
        height_span_bins=span_r,
        point_count=len(points),
        continuity=float(continuity),
        gap_fraction=float(gap_fraction),
        slope=slope,
        curvature=curvature,
        interference_overlap=ov,
        quality_status=q,
        member_component_ids=[component_id],
        component_confidence=conf,
        floor_overlap_fraction=floor_ov,
    )
    return rec
