"""Local width measurements in clearly separated coordinate systems.

Project geometry heuristics (not physical ionogram thresholds)
--------------------------------------------------------------
ANGLE_NEAR_AXIS_DEG (30):
    If the local tangent is within this angle of a fixed axis, a cut along
    that axis is treated as near-tangent (along-ridge), not transverse.
    Fixed-H invalid reason: axis_tangent_to_trace
    Fixed-V invalid reason: axis_tangent_to_trace

MULTI_INTERSECTION_MIN_SUPPORT (3 bins):
    Secondary ridge mass on a cut with a different branch label, or a
    second disconnected peak of comparable amplitude, rejects the sample
    (multiple_intersection / branch_overlap).

ALONG_RIDGE_SUPPORT_RATIO (2.5):
    If the estimated cut width exceeds this multiple of the thin baseline
    *and* the cut is poorly transverse, reject as along-ridge dominated.

Branch isolation:
    Each branch owns its labeled support. Other-branch pixels are zeroed
    in every cut. Uncertain overlapping labels reject the sample.

Aggregate frame widths use only valid branch-local samples; disagreement
across branches can make the aggregate unavailable.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import CenterlineRecord, MeasuredFeature

THIN_RIDGE_BASELINE_BINS = 1.0

# --- documented project geometry heuristics ---
ANGLE_NEAR_AXIS_DEG = 30.0
MULTI_INTERSECTION_MIN_SUPPORT = 3
ALONG_RIDGE_SUPPORT_RATIO = 2.5
BRANCH_AGREE_REL_TOL = 0.45


def _fwhm(profile: np.ndarray) -> tuple[float | None, str]:
    if profile.size < 3 or not np.isfinite(profile).all():
        return None, "insufficient_coverage"
    peak = float(np.max(profile))
    if peak <= 0 or not np.isfinite(peak):
        return None, "no_peak"
    half = 0.5 * peak
    above = np.where(profile >= half)[0]
    if above.size == 0:
        return None, "fit_failed"
    return float(above.max() - above.min() + 1), ""


def _percentile_width(profile: np.ndarray, lo: float = 25.0, hi: float = 75.0) -> tuple[float | None, str]:
    if profile.size < 3 or float(np.nansum(profile)) <= 0 or not np.isfinite(profile).any():
        return None, "insufficient_coverage"
    mass = np.clip(np.nan_to_num(profile, nan=0.0), 0, None)
    if mass.sum() <= 0:
        return None, "no_peak"
    cdf = np.cumsum(mass)
    cdf /= cdf[-1]
    i_lo = int(np.searchsorted(cdf, lo / 100.0))
    i_hi = int(np.searchsorted(cdf, hi / 100.0))
    return float(max(i_hi - i_lo, 0) + 1), ""


def _second_moment_width(profile: np.ndarray) -> tuple[float | None, str]:
    if profile.size < 3 or not np.isfinite(profile).any():
        return None, "insufficient_coverage"
    mass = np.clip(np.nan_to_num(profile, nan=0.0), 0, None)
    s = float(mass.sum())
    if s <= 0:
        return None, "no_peak"
    idx = np.arange(profile.size, dtype=float)
    mu = float(np.sum(idx * mass) / s)
    var = float(np.sum(mass * (idx - mu) ** 2) / s)
    return float(2.0 * np.sqrt(max(var, 0.0))), ""


def _support_width(profile: np.ndarray, thr_frac: float = 0.15) -> tuple[float | None, str]:
    if profile.size < 3:
        return None, "insufficient_coverage"
    peak = float(np.nanmax(profile))
    if peak <= 0 or not np.isfinite(peak):
        return None, "no_peak"
    above = np.where(profile >= thr_frac * peak)[0]
    if above.size == 0:
        return None, "fit_failed"
    return float(above.max() - above.min() + 1), ""


def _estimate_all(profile: np.ndarray) -> dict[str, dict[str, Any]]:
    out = {}
    for name, fn in (
        ("fwhm", _fwhm),
        ("robust_percentile", lambda p: _percentile_width(p)),
        ("second_moment", _second_moment_width),
        ("connected_support", _support_width),
    ):
        val, reason = fn(profile)
        out[name] = {"value": val, "valid": val is not None, "reason_invalid": reason, "estimator": name}
    return out


def _estimator_disagreement(est: dict[str, dict[str, Any]]) -> float | None:
    vals = [float(v["value"]) for v in est.values() if v.get("valid") and v.get("value") is not None]
    if len(vals) < 2:
        return None
    return float(np.std(vals) / (np.median(vals) + 1e-9))


def _local_slopes(points: list[tuple[int, int]], half: int = 3) -> dict[int, float]:
    """Local dr/dc at each column from neighboring centerline points."""
    if not points:
        return {}
    pts = sorted(points, key=lambda p: p[1])
    cs = [p[1] for p in pts]
    rs = [p[0] for p in pts]
    out: dict[int, float] = {}
    for i, (r, c) in enumerate(pts):
        lo = max(0, i - half)
        hi = min(len(pts), i + half + 1)
        if hi - lo < 2:
            out[c] = 0.0
            continue
        x = np.asarray(cs[lo:hi], dtype=float)
        y = np.asarray(rs[lo:hi], dtype=float)
        if np.allclose(x, x[0]):
            out[c] = 1e6  # nearly vertical column stack
        else:
            out[c] = float(np.polyfit(x, y, 1)[0])
    return out


def _angles_from_slope(slope: float) -> tuple[float, float]:
    """Return (angle_from_freq_deg, angle_from_height_deg)."""
    s = abs(float(slope))
    if not np.isfinite(s):
        s = 1e6
    ang_freq = float(np.degrees(np.arctan(s)))  # 0=horizontal, 90=vertical
    ang_height = 90.0 - ang_freq
    return ang_freq, ang_height


def _h_applicable(slope: float) -> tuple[bool, str]:
    ang_freq, _ = _angles_from_slope(slope)
    if ang_freq < ANGLE_NEAR_AXIS_DEG:
        return False, "axis_tangent_to_trace"
    return True, ""


def _v_applicable(slope: float) -> tuple[bool, str]:
    _, ang_height = _angles_from_slope(slope)
    if ang_height < ANGLE_NEAR_AXIS_DEG:
        return False, "axis_tangent_to_trace"
    return True, ""


def _count_label_support(labels: np.ndarray, own_id: int) -> tuple[int, int, set[int]]:
    """Return (own_support, other_support, other_ids) for positive labels on a 1D cut."""
    labs = labels[labels > 0]
    if labs.size == 0:
        return 0, 0, set()
    own = int((labs == own_id).sum())
    others = labs[labs != own_id]
    other_ids = set(int(x) for x in np.unique(others))
    return own, int(others.size), other_ids


def _secondary_peak_mass(profile: np.ndarray, center_idx: int) -> bool:
    """True if a second disconnected peak of comparable amplitude exists."""
    if profile.size < 5:
        return False
    mass = np.clip(np.nan_to_num(profile, nan=0.0), 0, None)
    peak = float(mass.max())
    if peak <= 0:
        return False
    thr = 0.35 * peak
    above = mass >= thr
    # connected components on 1D
    flips = np.diff(above.astype(np.int8))
    starts = list(np.where(flips == 1)[0] + 1)
    if above[0]:
        starts = [0] + starts
    ends = list(np.where(flips == -1)[0])
    if above[-1]:
        ends = ends + [len(above) - 1]
    segments = list(zip(starts, ends))
    if len(segments) <= 1:
        return False
    # more than one significant segment
    sig = 0
    for a, b in segments:
        if (b - a + 1) >= MULTI_INTERSECTION_MIN_SUPPORT and float(mass[a : b + 1].max()) >= thr:
            sig += 1
    return sig >= 2


def measure_local_widths(
    raw: np.ndarray,
    accepted: np.ndarray,
    interference: np.ndarray,
    centerlines: list[CenterlineRecord],
    floor_clutter: np.ndarray | None = None,
    branch_labels: np.ndarray | None = None,
    *,
    oversegmentation_suspected: bool = False,
) -> tuple[dict[str, MeasuredFeature], dict[str, np.ndarray], list[dict[str, Any]]]:
    h, w = raw.shape
    x = raw.astype(np.float64)
    v_map = np.full((h, w), np.nan, dtype=float)
    h_map = np.full((h, w), np.nan, dtype=float)
    n_map = np.full((h, w), np.nan, dtype=float)
    fixed_h_map = np.full((h, w), np.nan, dtype=float)
    applicability_h_map = np.zeros((h, w), dtype=np.uint8)
    applicability_v_map = np.zeros((h, w), dtype=np.uint8)
    feats: dict[str, MeasuredFeature] = {}
    excluded_regions = interference.copy()
    if floor_clutter is not None:
        excluded_regions = excluded_regions | floor_clutter
    if branch_labels is None:
        branch_labels = np.zeros((h, w), dtype=np.int32)

    width_ids = (
        "v2_fixed_vertical_axis_width_bins",
        "v2_fixed_horizontal_axis_width_bins",
        "v2_normal_to_ridge_width_bins",
        "v2_normal_width_baseline_residual_bins",
        "v2_true_slope_compensated_horizontal_residual_bins",
        "v2_along_ridge_support_length_bins",
        "v2_median_local_vertical_width_bins",
        "v2_median_local_horizontal_width_bins",
        "v2_local_vertical_width_max",
        "v2_local_horizontal_width_max",
        "v2_vertical_width_elevated_fraction",
        "v2_horizontal_width_elevated_fraction",
        "v2_vertical_contiguous_broadening_length",
        "v2_horizontal_contiguous_broadening_length",
        "v2_coexistence_score",
        "v2_width_balance_ratio",
        "v2_width_estimator_disagreement",
        "v2_width_valid_count",
        "v2_width_excluded_count",
        "v2_width_fwhm_bins",
        "v2_width_second_moment_bins",
        "v2_width_connected_support_bins",
        "v2_width_estimators_available",
        "v2_horizontal_axis_width_applicable_fraction",
        "v2_vertical_axis_width_applicable_fraction",
        "v2_axis_tangent_rejection_count",
        "v2_multiple_intersection_rejection_count",
        "v2_branch_overlap_rejection_count",
        "v2_width_aggregate_branches_contributed",
        "v2_width_aggregate_branches_agree",
        "v2_width_aggregate_dominant_branch_id",
        "v2_coexistence_fraction",
    )

    empty_maps = {
        "vertical_width_map": v_map,
        "horizontal_width_map": h_map,
        "normal_to_ridge_width_map": n_map,
        "fixed_horizontal_width_map": fixed_h_map,
        "horizontal_applicability_map": applicability_h_map,
        "vertical_applicability_map": applicability_v_map,
    }

    if not centerlines or not accepted.any():
        for fid in width_ids:
            feats[fid] = MeasuredFeature(
                fid, None, unit="bins", valid=False,
                reason_invalid="trace_not_found", confidence_status="abstain",
            )
        return feats, empty_maps, []

    # Per-branch sample collections
    branch_width_records: list[dict[str, Any]] = []
    all_vert: list[tuple[int, int, float]] = []  # (branch_id, col, value)
    all_fixed_h: list[tuple[int, int, float]] = []
    all_normal: list[tuple[int, int, float]] = []
    all_resid_n: list[tuple[int, int, float]] = []
    all_true_h: list[tuple[int, int, float]] = []
    excl = 0
    valid_n = 0
    axis_tangent_rej = 0
    multi_inter_rej = 0
    branch_overlap_rej = 0
    h_applicable_tries = 0
    h_applicable_ok = 0
    v_applicable_tries = 0
    v_applicable_ok = 0
    disagreements: list[float] = []
    fwhm_vals: list[float] = []
    sm_vals: list[float] = []
    cs_vals: list[float] = []
    conf = "low" if oversegmentation_suspected else "medium"

    for cl in centerlines:
        bid = int(cl.branch_id)
        local_slope = _local_slopes(cl.points_rc)
        col_to_row = {c: r for r, c in cl.points_rc}
        b_vert: dict[int, float] = {}
        b_fixed_h: dict[int, float] = {}
        b_normal: dict[int, float] = {}
        b_resid_n: dict[int, float] = {}
        b_true_h: dict[int, float] = {}
        b_h_reasons: dict[str, int] = {}
        b_v_reasons: dict[str, int] = {}
        b_h_tried = b_h_ok = b_v_tried = b_v_ok = 0

        for c, r0 in col_to_row.items():
            if excluded_regions[:, c].mean() > 0.55:
                excl += 1
                continue
            r0 = int(np.clip(r0, 0, h - 1))
            slope = local_slope.get(c, cl.slope)
            ang_freq, ang_height = _angles_from_slope(slope)
            h_ok, h_reason = _h_applicable(slope)
            v_ok, v_reason = _v_applicable(slope)

            # --- Fixed vertical cut (range/height axis) ---
            v_applicable_tries += 1
            b_v_tried += 1
            if not v_ok:
                axis_tangent_rej += 1
                b_v_reasons[v_reason] = b_v_reasons.get(v_reason, 0) + 1
            else:
                lo, hi = max(0, r0 - 20), min(h, r0 + 21)
                profile = x[lo:hi, c].copy()
                lab_cut = branch_labels[lo:hi, c].copy()
                near = 4  # bins around centerline — local separability window
                cidx = r0 - lo
                near_other = False
                for rr in range(lo, hi):
                    i = rr - lo
                    if excluded_regions[rr, c]:
                        profile[i] = 0.0
                    elif lab_cut[i] > 0 and lab_cut[i] != bid:
                        # Far other-branch mass is zeroed (isolation); near overlap rejects
                        if abs(i - cidx) <= near:
                            near_other = True
                        profile[i] = 0.0
                if near_other:
                    multi_inter_rej += 1
                    branch_overlap_rej += 1
                    b_v_reasons["branch_overlap"] = b_v_reasons.get("branch_overlap", 0) + 1
                    excl += 1
                elif _secondary_peak_mass(profile, cidx):
                    multi_inter_rej += 1
                    b_v_reasons["multiple_intersection"] = b_v_reasons.get("multiple_intersection", 0) + 1
                    excl += 1
                else:
                    profile = np.clip(profile - np.median(profile), 0, None)
                    est = _estimate_all(profile)
                    chosen = est["robust_percentile"]
                    if chosen["valid"] and chosen["value"] is not None and np.isfinite(chosen["value"]):
                        wv = float(chosen["value"])
                        if wv > ALONG_RIDGE_SUPPORT_RATIO * THIN_RIDGE_BASELINE_BINS * 8 and ang_height < ANGLE_NEAR_AXIS_DEG + 10:
                            axis_tangent_rej += 1
                            b_v_reasons["along_ridge_dominated"] = b_v_reasons.get("along_ridge_dominated", 0) + 1
                        else:
                            b_vert[c] = wv
                            all_vert.append((bid, c, wv))
                            v_map[r0, c] = wv
                            applicability_v_map[r0, c] = 1
                            v_applicable_ok += 1
                            b_v_ok += 1
                            valid_n += 1
                            d = _estimator_disagreement(est)
                            if d is not None:
                                disagreements.append(d)
                            fv, _ = _fwhm(profile)
                            if fv is not None:
                                fwhm_vals.append(fv)
                            sv, _ = _second_moment_width(profile)
                            if sv is not None:
                                sm_vals.append(sv)
                            cv, _ = _support_width(profile)
                            if cv is not None:
                                cs_vals.append(cv)
                    else:
                        excl += 1

            # --- Fixed horizontal cut (frequency axis) ---
            h_applicable_tries += 1
            b_h_tried += 1
            if not h_ok:
                axis_tangent_rej += 1
                b_h_reasons[h_reason] = b_h_reasons.get(h_reason, 0) + 1
            else:
                clo, chi = max(0, c - 20), min(w, c + 21)
                hprof = x[r0, clo:chi].copy()
                lab_h = branch_labels[r0, clo:chi].copy()
                cidx = c - clo
                near = 4
                near_other = False
                for cc in range(clo, chi):
                    i = cc - clo
                    if excluded_regions[r0, cc]:
                        hprof[i] = np.nan
                    elif lab_h[i] > 0 and lab_h[i] != bid:
                        if abs(i - cidx) <= near:
                            near_other = True
                        hprof[i] = np.nan
                if near_other:
                    multi_inter_rej += 1
                    branch_overlap_rej += 1
                    b_h_reasons["branch_overlap"] = b_h_reasons.get("branch_overlap", 0) + 1
                elif np.isfinite(hprof).sum() >= 7:
                    finite = hprof[np.isfinite(hprof)]
                    bg = float(np.median(np.r_[finite[:3], finite[-3:]])) if finite.size >= 6 else float(np.nanmedian(hprof))
                    hprof_z = np.nan_to_num(np.clip(hprof - bg, 0, None), nan=0.0)
                    if _secondary_peak_mass(hprof_z, cidx):
                        multi_inter_rej += 1
                        b_h_reasons["multiple_intersection"] = b_h_reasons.get("multiple_intersection", 0) + 1
                    else:
                        hest = _estimate_all(hprof_z)
                        if hest["robust_percentile"]["valid"] and hest["robust_percentile"]["value"] is not None:
                            wh = float(hest["robust_percentile"]["value"])
                            if wh > ALONG_RIDGE_SUPPORT_RATIO * THIN_RIDGE_BASELINE_BINS * 8 and ang_freq < ANGLE_NEAR_AXIS_DEG + 10:
                                axis_tangent_rej += 1
                                b_h_reasons["along_ridge_dominated"] = b_h_reasons.get("along_ridge_dominated", 0) + 1
                            else:
                                b_fixed_h[c] = wh
                                all_fixed_h.append((bid, c, wh))
                                fixed_h_map[r0, c] = wh
                                applicability_h_map[r0, c] = 1
                                h_applicable_ok += 1
                                b_h_ok += 1

            # --- Local normal-to-ridge (always geometrically preferred when separable) ---
            tang = float(np.hypot(slope if abs(slope) < 1e5 else 1e5, 1.0)) + 1e-9
            n_r = -1.0 / tang
            n_c = (slope if abs(slope) < 1e5 else 1e5) / tang
            half = 12
            prof = []
            lab_n = []
            for k in range(-half, half + 1):
                r = int(np.clip(round(r0 + k * n_r), 0, h - 1))
                cc = int(np.clip(round(c + k * n_c), 0, w - 1))
                lab_n.append(int(branch_labels[r, cc]))
                if excluded_regions[r, cc] or (branch_labels[r, cc] > 0 and branch_labels[r, cc] != bid):
                    prof.append(0.0)
                else:
                    prof.append(float(x[r, cc]))
            lab_n_arr = np.asarray(lab_n, dtype=int)
            near_other_n = any(
                lab_n_arr[i] > 0 and lab_n_arr[i] != bid and abs(i - half) <= 4
                for i in range(len(lab_n_arr))
            )
            if near_other_n:
                multi_inter_rej += 1
                branch_overlap_rej += 1
            elif len(prof) >= 7:
                profile = np.asarray(prof, dtype=float)
                if _secondary_peak_mass(profile, half):
                    multi_inter_rej += 1
                else:
                    bg = float(np.median(np.r_[profile[:3], profile[-3:]]))
                    profile = np.clip(profile - bg, 0, None)
                    nest = _estimate_all(profile)
                    if nest["robust_percentile"]["valid"] and nest["robust_percentile"]["value"] is not None:
                        nw = float(nest["robust_percentile"]["value"])
                        if np.isfinite(nw):
                            b_normal[c] = nw
                            all_normal.append((bid, c, nw))
                            n_map[r0, c] = nw
                            rn = max(nw - THIN_RIDGE_BASELINE_BINS, 0.0)
                            b_resid_n[c] = rn
                            all_resid_n.append((bid, c, rn))
                            h_map[r0, c] = rn
                            fh = b_fixed_h.get(c)
                            if fh is not None:
                                projected_thin = THIN_RIDGE_BASELINE_BINS / max(abs(n_c), 0.15)
                                thr = max(fh - projected_thin, 0.0)
                                b_true_h[c] = thr
                                all_true_h.append((bid, c, thr))

        along = float(cl.frequency_span_bins[1] - cl.frequency_span_bins[0] + 1)
        branch_width_records.append(
            {
                "branch_id": bid,
                "point_count": cl.point_count,
                "along_ridge_support_length_bins": along,
                "fixed_vertical": {
                    "valid_sample_count": len(b_vert),
                    "tried": b_v_tried,
                    "applicable_ok": b_v_ok,
                    "applicability_fraction": float(b_v_ok / max(b_v_tried, 1)),
                    "median": float(np.median(list(b_vert.values()))) if b_vert else None,
                    "uncertainty": float(np.std(list(b_vert.values()))) if len(b_vert) > 1 else None,
                    "invalid_reasons": dict(b_v_reasons),
                    "contiguous_valid_columns": _contig_cols(sorted(b_vert)),
                },
                "fixed_horizontal": {
                    "valid_sample_count": len(b_fixed_h),
                    "tried": b_h_tried,
                    "applicable_ok": b_h_ok,
                    "applicability_fraction": float(b_h_ok / max(b_h_tried, 1)),
                    "median": float(np.median(list(b_fixed_h.values()))) if b_fixed_h else None,
                    "uncertainty": float(np.std(list(b_fixed_h.values()))) if len(b_fixed_h) > 1 else None,
                    "invalid_reasons": dict(b_h_reasons),
                    "contiguous_valid_columns": _contig_cols(sorted(b_fixed_h)),
                },
                "normal_to_ridge": {
                    "valid_sample_count": len(b_normal),
                    "median": float(np.median(list(b_normal.values()))) if b_normal else None,
                    "uncertainty": float(np.std(list(b_normal.values()))) if len(b_normal) > 1 else None,
                },
                "true_slope_compensated_horizontal_residual": {
                    "valid_sample_count": len(b_true_h),
                    "median": float(np.median(list(b_true_h.values()))) if b_true_h else None,
                },
            }
        )

    def _agg_from_samples(
        name: str,
        samples: list[tuple[int, int, float]],
        unit: str = "bins",
    ) -> None:
        if not samples:
            feats[name] = MeasuredFeature(
                name, None, unit=unit, valid=False, reason_invalid="insufficient_coverage",
                confidence_status="abstain",
                metadata={
                    "excluded_sample_count": excl,
                    "axis_tangent_rejection_count": axis_tangent_rej,
                    "heuristics": {
                        "ANGLE_NEAR_AXIS_DEG": ANGLE_NEAR_AXIS_DEG,
                        "MULTI_INTERSECTION_MIN_SUPPORT": MULTI_INTERSECTION_MIN_SUPPORT,
                    },
                },
            )
            return
        by_branch: dict[int, list[float]] = {}
        for bid, _c, v in samples:
            by_branch.setdefault(bid, []).append(v)
        medians = {b: float(np.median(vs)) for b, vs in by_branch.items()}
        vals = [v for _b, _c, v in samples]
        arr = np.asarray(vals, dtype=float)
        # Agreement across branches
        agree = True
        if len(medians) >= 2:
            mvals = list(medians.values())
            agree = (max(mvals) - min(mvals)) <= BRANCH_AGREE_REL_TOL * (np.median(mvals) + 1e-9) + 2.0
        dominant = max(by_branch.items(), key=lambda kv: len(kv[1]))[0]
        if not agree and len(medians) >= 2:
            feats[name] = MeasuredFeature(
                name, None, unit=unit, valid=False,
                reason_invalid="branch_disagreement",
                confidence_status="abstain",
                metadata={
                    "branches_contributed": sorted(medians),
                    "branch_medians": medians,
                    "branches_agree": False,
                    "dominant_branch_id": dominant,
                    "valid_sample_count": int(arr.size),
                },
            )
            return
        feats[name] = MeasuredFeature(
            name, float(np.median(arr)), unit=unit, valid=True,
            uncertainty=float(np.std(arr)) if arr.size > 1 else None,
            confidence_status=conf, estimator="robust_percentile",
            metadata={
                "valid_sample_count": int(arr.size),
                "excluded_sample_count": excl,
                "branches_contributed": sorted(medians),
                "branch_medians": medians,
                "branches_agree": agree,
                "dominant_branch_id": dominant,
                "one_branch_dominates": len(by_branch) == 1 or (
                    len(by_branch.get(dominant, [])) >= 0.7 * len(samples)
                ),
            },
        )

    _agg_from_samples("v2_fixed_vertical_axis_width_bins", all_vert)
    _agg_from_samples("v2_fixed_horizontal_axis_width_bins", all_fixed_h)
    _agg_from_samples("v2_normal_to_ridge_width_bins", all_normal)
    _agg_from_samples("v2_normal_width_baseline_residual_bins", all_resid_n)
    _agg_from_samples("v2_true_slope_compensated_horizontal_residual_bins", all_true_h)

    # Along-ridge: sum/max of branch supports — use longest branch length, not silent sole truth
    along_vals = [float(r["along_ridge_support_length_bins"]) for r in branch_width_records]
    feats["v2_along_ridge_support_length_bins"] = MeasuredFeature(
        "v2_along_ridge_support_length_bins",
        float(max(along_vals)) if along_vals else None,
        unit="bins", valid=bool(along_vals),
        reason_invalid="" if along_vals else "trace_not_found",
        confidence_status=conf if along_vals else "abstain",
        metadata={"per_branch": along_vals, "note": "max across branches; see branch_records"},
    )

    # Applicability fractions
    feats["v2_horizontal_axis_width_applicable_fraction"] = MeasuredFeature(
        "v2_horizontal_axis_width_applicable_fraction",
        float(h_applicable_ok / max(h_applicable_tries, 1)),
        unit="fraction", valid=h_applicable_tries > 0,
        reason_invalid="" if h_applicable_tries else "trace_not_found",
        confidence_status="medium",
        metadata={
            "tried": h_applicable_tries, "ok": h_applicable_ok,
            "ANGLE_NEAR_AXIS_DEG": ANGLE_NEAR_AXIS_DEG,
            "note": "project geometry heuristic",
        },
    )
    feats["v2_vertical_axis_width_applicable_fraction"] = MeasuredFeature(
        "v2_vertical_axis_width_applicable_fraction",
        float(v_applicable_ok / max(v_applicable_tries, 1)),
        unit="fraction", valid=v_applicable_tries > 0,
        reason_invalid="" if v_applicable_tries else "trace_not_found",
        confidence_status="medium",
        metadata={
            "tried": v_applicable_tries, "ok": v_applicable_ok,
            "ANGLE_NEAR_AXIS_DEG": ANGLE_NEAR_AXIS_DEG,
            "note": "project geometry heuristic",
        },
    )
    feats["v2_axis_tangent_rejection_count"] = MeasuredFeature(
        "v2_axis_tangent_rejection_count", float(axis_tangent_rej), unit="count",
        valid=True, confidence_status="high",
    )
    feats["v2_multiple_intersection_rejection_count"] = MeasuredFeature(
        "v2_multiple_intersection_rejection_count", float(multi_inter_rej), unit="count",
        valid=True, confidence_status="high",
    )
    feats["v2_branch_overlap_rejection_count"] = MeasuredFeature(
        "v2_branch_overlap_rejection_count", float(branch_overlap_rej), unit="count",
        valid=True, confidence_status="high",
    )

    # Aggregate provenance
    contrib = sorted({b for b, _c, _v in (all_vert + all_fixed_h + all_normal)})
    feats["v2_width_aggregate_branches_contributed"] = MeasuredFeature(
        "v2_width_aggregate_branches_contributed", float(len(contrib)), unit="count",
        valid=True, confidence_status="high", metadata={"branch_ids": contrib},
    )
    v_meta = feats["v2_fixed_vertical_axis_width_bins"].metadata
    h_meta = feats["v2_fixed_horizontal_axis_width_bins"].metadata
    agree = bool(v_meta.get("branches_agree", True) and h_meta.get("branches_agree", True))
    feats["v2_width_aggregate_branches_agree"] = MeasuredFeature(
        "v2_width_aggregate_branches_agree", 1.0 if agree else 0.0, unit="flag",
        valid=True, confidence_status="medium",
    )
    dom = v_meta.get("dominant_branch_id") or h_meta.get("dominant_branch_id")
    feats["v2_width_aggregate_dominant_branch_id"] = MeasuredFeature(
        "v2_width_aggregate_dominant_branch_id",
        float(dom) if dom is not None else None,
        unit="id", valid=dom is not None,
        reason_invalid="" if dom is not None else "trace_not_found",
        confidence_status="medium" if dom is not None else "abstain",
    )

    # Compatibility aliases — only from applicable/valid aggregates
    fv = feats.get("v2_fixed_vertical_axis_width_bins")
    if fv:
        feats["v2_median_local_vertical_width_bins"] = MeasuredFeature(
            feature_id="v2_median_local_vertical_width_bins", value=fv.value, unit=fv.unit,
            valid=fv.valid, uncertainty=fv.uncertainty, confidence_status=fv.confidence_status,
            reason_invalid=fv.reason_invalid, estimator=fv.estimator,
            metadata={**fv.metadata, "alias_of": "v2_fixed_vertical_axis_width_bins"},
        )
    # Legacy horizontal alias: prefer true H residual when valid; else abstain (do not use tangent junk)
    sh = feats.get("v2_true_slope_compensated_horizontal_residual_bins")
    if sh is None or not sh.valid:
        # Prefer fixed-H itself when applicable; never substitute elevated tangent residual
        sh = feats.get("v2_fixed_horizontal_axis_width_bins")
    if sh is None or not sh.valid:
        sh = MeasuredFeature(
            "v2_median_local_horizontal_width_bins", None, unit="bins", valid=False,
            reason_invalid="axis_not_applicable_or_insufficient", confidence_status="abstain",
        )
        feats["v2_median_local_horizontal_width_bins"] = sh
    else:
        feats["v2_median_local_horizontal_width_bins"] = MeasuredFeature(
            feature_id="v2_median_local_horizontal_width_bins", value=sh.value, unit=sh.unit,
            valid=sh.valid, uncertainty=sh.uncertainty, confidence_status=sh.confidence_status,
            reason_invalid=sh.reason_invalid, estimator=sh.estimator,
            metadata={**sh.metadata, "alias_of": sh.feature_id},
        )

    def _contig(by_col: dict[int, float], thr: float) -> float:
        if not by_col:
            return 0.0
        cols = sorted(by_col)
        run = max_run = 0
        prev = None
        for c in cols:
            if by_col[c] < thr:
                run = 0
                prev = c
                continue
            if prev is not None and c - prev > 1:
                run = 0
            run += 1
            max_run = max(max_run, run)
            prev = c
        return float(max_run)

    vert_by_col = {c: v for _b, c, v in all_vert}
    if vert_by_col:
        vals = list(vert_by_col.values())
        feats["v2_local_vertical_width_max"] = MeasuredFeature(
            "v2_local_vertical_width_max", float(np.max(vals)), unit="bins", valid=True, confidence_status=conf,
        )
        elev_thr = max(float(np.median(vals)) * 1.5, 4.0)
        elev = float(np.mean(np.asarray(vals) >= elev_thr))
        feats["v2_vertical_width_elevated_fraction"] = MeasuredFeature(
            "v2_vertical_width_elevated_fraction", elev, unit="fraction", valid=True, confidence_status=conf,
            metadata={"threshold_bins": elev_thr},
        )
        feats["v2_vertical_contiguous_broadening_length"] = MeasuredFeature(
            "v2_vertical_contiguous_broadening_length", _contig(vert_by_col, elev_thr),
            unit="samples", valid=True, confidence_status=conf,
        )
    else:
        for fid in (
            "v2_local_vertical_width_max",
            "v2_vertical_width_elevated_fraction",
            "v2_vertical_contiguous_broadening_length",
        ):
            feats[fid] = MeasuredFeature(
                fid, None, unit="bins", valid=False, reason_invalid="insufficient_coverage", confidence_status="abstain",
            )

    # Horizontal broadening source: fixed-H residual only when applicable (not normal-as-horizontal)
    hsrc = {c: v for _b, c, v in all_true_h} or {c: v for _b, c, v in all_fixed_h}
    if hsrc:
        vals = list(hsrc.values())
        feats["v2_local_horizontal_width_max"] = MeasuredFeature(
            "v2_local_horizontal_width_max", float(np.max(vals)), unit="bins", valid=True, confidence_status=conf,
        )
        elev_thr = max(float(np.median(vals)) * 1.5, 3.0)
        elev = float(np.mean(np.asarray(vals) >= elev_thr))
        feats["v2_horizontal_width_elevated_fraction"] = MeasuredFeature(
            "v2_horizontal_width_elevated_fraction", elev, unit="fraction", valid=True, confidence_status=conf,
            metadata={"threshold_bins": elev_thr},
        )
        feats["v2_horizontal_contiguous_broadening_length"] = MeasuredFeature(
            "v2_horizontal_contiguous_broadening_length", _contig(hsrc, elev_thr),
            unit="samples", valid=True, confidence_status=conf,
        )
    else:
        for fid in (
            "v2_local_horizontal_width_max",
            "v2_horizontal_width_elevated_fraction",
            "v2_horizontal_contiguous_broadening_length",
        ):
            feats[fid] = MeasuredFeature(
                fid, None, unit="bins", valid=False, reason_invalid="axis_not_applicable_or_insufficient",
                confidence_status="abstain",
            )

    common = set(vert_by_col) & set(hsrc)
    if common:
        v_thr = max(float(np.median(list(vert_by_col.values()))) * 1.5, 4.0)
        h_thr = max(float(np.median(list(hsrc.values()))) * 1.5, 3.0)
        both = sum(1 for c in common if vert_by_col[c] >= v_thr and hsrc[c] >= h_thr)
        score = float(both / len(common))
        feats["v2_coexistence_score"] = MeasuredFeature(
            "v2_coexistence_score", score, unit="score", valid=True, confidence_status="low",
            metadata={"matched_columns": len(common), "note": "not_a_fraction_of_frame; matched_positions"},
        )
        bal = float(np.median([hsrc[c] for c in common])) / (float(np.median([vert_by_col[c] for c in common])) + 1e-9)
        feats["v2_width_balance_ratio"] = MeasuredFeature(
            "v2_width_balance_ratio", bal, unit="ratio", valid=True, confidence_status="low",
        )
    else:
        feats["v2_coexistence_score"] = MeasuredFeature(
            "v2_coexistence_score", None, unit="score", valid=False,
            reason_invalid="insufficient_coverage", confidence_status="abstain",
        )
        feats["v2_width_balance_ratio"] = MeasuredFeature(
            "v2_width_balance_ratio", None, unit="ratio", valid=False,
            reason_invalid="insufficient_coverage", confidence_status="abstain",
        )

    feats["v2_width_estimators_available"] = MeasuredFeature(
        "v2_width_estimators_available",
        "fwhm,robust_percentile,second_moment,connected_support",
        unit="text", valid=True, confidence_status="high",
    )
    feats["v2_width_estimator_disagreement"] = MeasuredFeature(
        "v2_width_estimator_disagreement",
        float(np.median(disagreements)) if disagreements else None,
        unit="ratio", valid=bool(disagreements),
        reason_invalid="" if disagreements else "insufficient_coverage",
        confidence_status=conf if disagreements else "abstain",
    )
    feats["v2_width_valid_count"] = MeasuredFeature(
        "v2_width_valid_count", float(valid_n), unit="count", valid=True, confidence_status="high",
    )
    feats["v2_width_excluded_count"] = MeasuredFeature(
        "v2_width_excluded_count", float(excl), unit="count", valid=True, confidence_status="high",
    )
    for fid, vals in (
        ("v2_width_fwhm_bins", fwhm_vals),
        ("v2_width_second_moment_bins", sm_vals),
        ("v2_width_connected_support_bins", cs_vals),
    ):
        feats[fid] = MeasuredFeature(
            fid, float(np.median(vals)) if vals else None, unit="bins",
            valid=bool(vals), reason_invalid="" if vals else "insufficient_coverage",
            confidence_status=conf if vals else "abstain",
        )

    feats["v2_coexistence_fraction"] = MeasuredFeature(
        "v2_coexistence_fraction", None, unit="fraction", valid=False,
        reason_invalid="replaced_by_v2_coexistence_score", confidence_status="abstain",
        metadata={"use": "v2_coexistence_score"},
    )

    return feats, {
        "vertical_width_map": v_map,
        "horizontal_width_map": h_map,
        "normal_to_ridge_width_map": n_map,
        "fixed_horizontal_width_map": fixed_h_map,
        "horizontal_applicability_map": applicability_h_map,
        "vertical_applicability_map": applicability_v_map,
    }, branch_width_records


def _contig_cols(cols: list[int]) -> int:
    if not cols:
        return 0
    run = max_run = 1
    for i in range(1, len(cols)):
        if cols[i] - cols[i - 1] == 1:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    return int(max_run)
