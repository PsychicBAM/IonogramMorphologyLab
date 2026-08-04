#!/usr/bin/env python3
"""Strict synthetic geometry — H/V independence, axis applicability, branch isolation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.synthetic_geometry import GEOMETRY_CASES, generate_geometry_case
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION

OUT = ROOT / "docs" / "_phase4b3_iml2-0.2.0_synthetic_geometry"


def _f(res, fid):
    return res.features.get(fid)


def _val(feat):
    if feat is None or not feat.valid or feat.value is None:
        return None
    return float(feat.value)


def evaluate(name: str, res, baselines: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            reasons.append(msg)

    thin_diag = baselines["thin_diagonal_baseline"]
    thin_horiz = baselines["thin_horizontal_ridge"]
    thin_steep = baselines["thin_steep_baseline"]
    thin_shallow = baselines["thin_shallow_baseline"]
    thin_v = _f(thin_diag, "v2_fixed_vertical_axis_width_bins")
    thin_h = _f(thin_diag, "v2_fixed_horizontal_axis_width_bins")
    thin_n = _f(thin_diag, "v2_normal_to_ridge_width_bins")
    steep_h = _f(thin_steep, "v2_fixed_horizontal_axis_width_bins")
    shallow_v = _f(thin_shallow, "v2_fixed_vertical_axis_width_bins")

    if name == "thin_horizontal_ridge":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        bc = _f(res, "v2_consolidated_branch_count")
        need(bc is not None and bc.value is not None and 1 <= float(bc.value) <= 2, f"approx one branch, got {bc.value if bc else None}")
        nv = _f(res, "v2_normal_to_ridge_width_bins")
        need(nv is not None and nv.valid and float(nv.value) < 8, f"narrow normal width, got {nv.value if nv else None}")
        # Frequency-axis cut is tangent — must not report elevated residual as low-width evidence
        thr = _f(res, "v2_true_slope_compensated_horizontal_residual_bins")
        fh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        hap = _f(res, "v2_horizontal_axis_width_applicable_fraction")
        # Either H aggregate invalid / low applicability, or residual invalid / tiny
        h_ok = False
        if hap is not None and hap.valid and float(hap.value) < 0.25:
            h_ok = True
        if thr is not None and not thr.valid:
            h_ok = True
        if fh is not None and not fh.valid:
            h_ok = True
        if thr is not None and thr.valid and float(thr.value) < 2.0:
            h_ok = True
        # Explicitly reject the previous false ~8.8 elevated residual as "low width"
        if thr is not None and thr.valid and float(thr.value) >= 4.0:
            h_ok = False
            reasons.append(f"true_H residual falsely elevated on horizontal ridge: {thr.value}")
        need(h_ok, "horizontal cut must be invalid/tangent or low residual — not falsely elevated")
        at = _f(res, "v2_axis_tangent_rejection_count")
        need(at is not None and float(at.value or 0) > 0, "expected axis_tangent rejections on horizontal ridge")

    elif name == "thin_sloping_ridge":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        bc = _f(res, "v2_consolidated_branch_count")
        need(bc is not None and bc.value is not None and 1 <= float(bc.value) <= 2, f"approx one branch, got {bc.value if bc else None}")
        nv = _f(res, "v2_normal_to_ridge_width_bins")
        need(nv is not None and nv.valid and float(nv.value) < 10, f"low normal width, got {nv.value if nv else None}")

    elif name == "thin_diagonal_baseline":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        need(thin_v is not None and thin_v.valid, "fixed-V must be applicable/valid on diagonal baseline")
        need(thin_h is not None and thin_h.valid, "fixed-H must be applicable/valid on diagonal baseline")
        need(thin_n is not None and thin_n.valid and float(thin_n.value) < 8, "low normal width on thin baseline")
        thr = _f(res, "v2_true_slope_compensated_horizontal_residual_bins")
        if thr is not None and thr.valid:
            need(float(thr.value) < 6, f"false elevated H residual on thin diagonal: {thr.value}")

    elif name == "thin_steep_baseline":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        hh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        need(hh is not None and hh.valid, "fixed-H must be valid on steep baseline")
        # V near-tangent
        vap = _f(res, "v2_vertical_axis_width_applicable_fraction")
        need(
            (vv is not None and not vv.valid) or (vap is not None and float(vap.value or 0) < 0.35),
            "fixed-V should be largely inapplicable on steep baseline",
        )

    elif name == "thin_shallow_baseline":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        need(vv is not None and vv.valid, "fixed-V must be valid on shallow baseline")
        hap = _f(res, "v2_horizontal_axis_width_applicable_fraction")
        hh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        need(
            (hh is not None and not hh.valid) or (hap is not None and float(hap.value or 0) < 0.35),
            "fixed-H should be largely inapplicable on shallow baseline",
        )

    elif name == "thin_curved_ridge":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        nv = _f(res, "v2_normal_to_ridge_width_bins")
        need(nv is not None and nv.valid, "local-normal width must be valid")

    elif name == "vertically_broadened_ridge":
        # Range-axis-only vs paired thin_shallow_baseline
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        need(vv is not None and vv.valid, "vertical width must be valid")
        need(shallow_v is not None and shallow_v.valid, "shallow thin V baseline missing")
        if vv and vv.valid and shallow_v and shallow_v.valid:
            need(float(vv.value) > float(shallow_v.value) + 1.0, f"V {vv.value} not > shallow thin V {shallow_v.value}")
        hh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        hap = _f(res, "v2_horizontal_axis_width_applicable_fraction")
        need(
            (hh is not None and not hh.valid) or (hap is not None and float(hap.value or 0) < 0.35),
            "H should remain inapplicable/non-elevated on shallow V-broadened ridge",
        )

    elif name == "horizontally_broadened_ridge":
        # Frequency-axis-only vs paired thin_steep_baseline
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        hh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        need(hh is not None and hh.valid, "horizontal width must be valid where applicable")
        need(steep_h is not None and steep_h.valid, "steep thin H baseline missing")
        if hh and hh.valid and steep_h and steep_h.valid:
            need(float(hh.value) > float(steep_h.value) + 1.0, f"H {hh.value} not > steep thin H {steep_h.value}")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        vap = _f(res, "v2_vertical_axis_width_applicable_fraction")
        steep_v = _f(thin_steep, "v2_fixed_vertical_axis_width_bins")
        # V remains inapplicable, or not elevated vs steep thin (coupling may create weak V)
        v_ok = (
            (vv is not None and not vv.valid)
            or (vap is not None and float(vap.value or 0) < 0.35)
            or (
                vv is not None and vv.valid and steep_v is not None and steep_v.valid
                and float(vv.value) <= float(steep_v.value) + 1.5
            )
            or (vv is not None and vv.valid and hh is not None and hh.valid and float(vv.value) + 0.5 < float(hh.value))
        )
        need(v_ok, "V should stay inapplicable or non-elevated vs steep thin on H-only broadening")
        nv = _f(res, "v2_normal_to_ridge_width_bins")
        need(nv is not None and (nv.valid or bool(nv.reason_invalid)), "normal width must be reported")

    elif name == "broadened_both_axes":
        tr = _f(res, "v2_trace_pixel_fraction")
        need(tr is not None and tr.valid, "trace must be valid")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        hh = _f(res, "v2_fixed_horizontal_axis_width_bins")
        need(vv is not None and vv.valid and thin_v is not None and thin_v.valid, "V missing")
        need(hh is not None and hh.valid and thin_h is not None and thin_h.valid, "H missing")
        if vv and vv.valid and thin_v and thin_v.valid:
            need(float(vv.value) > float(thin_v.value) + 0.5, f"V not elevated: {vv.value} vs {thin_v.value}")
        if hh and hh.valid and thin_h and thin_h.valid:
            need(float(hh.value) > float(thin_h.value) + 0.5, f"H not elevated: {hh.value} vs {thin_h.value}")

    elif name == "two_parallel_branches":
        bc = _f(res, "v2_consolidated_branch_count")
        need(bc is not None and bc.value is not None and float(bc.value) >= 2, f"need >=2 branches, got {bc.value if bc else None}")
        sep = _f(res, "v2_branch_separation_bins")
        need(sep is not None and sep.valid, "separation must be valid")
        # Branch-local widths remain thin; separation must not become range-axis width
        for br in res.branch_records:
            w = (br.get("widths") or {}).get("fixed_vertical") or {}
            med = w.get("median")
            if med is not None:
                need(float(med) < 8.0, f"branch {br.get('branch_id')} V width {med} treats separation as width")
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        if vv is not None and vv.valid:
            need(float(vv.value) < 10.0, f"frame aggregate V {vv.value} inflated by inter-branch gap")

    elif name == "crossing_branches":
        bc = _f(res, "v2_consolidated_branch_count")
        multi = bc is not None and bc.value is not None and float(bc.value) >= 2
        amb = _f(res, "v2_ox_ambiguity_possibility")
        merge = _f(res, "v2_merge_split_locations")
        curv_amb = False
        if res.centerlines:
            curv_amb = any(float(c.curvature) >= 0.35 for c in res.centerlines) or any(
                abs(float(c.slope)) > 0.2 and float(c.point_count) > 40 for c in res.centerlines
            )
        explicit = (amb is not None and amb.valid and float(amb.value or 0) > 0) or (
            merge is not None and merge.valid and float(merge.value or 0) > 0
        ) or curv_amb
        need(multi or explicit, "crossing must yield multiple branches or explicit ambiguity")
        # Local widths near crossing: invalid / overlap rejections / ambiguity — not silent diffuse broadening
        mi = _f(res, "v2_multiple_intersection_rejection_count")
        bo = _f(res, "v2_branch_overlap_rejection_count")
        rejected = (mi is not None and float(mi.value or 0) > 0) or (bo is not None and float(bo.value or 0) > 0)
        vv = _f(res, "v2_fixed_vertical_axis_width_bins")
        false_broad = vv is not None and vv.valid and float(vv.value) >= 12.0
        if false_broad and not (rejected or multi or explicit):
            reasons.append(f"crossing produced false broadening V={vv.value} without ambiguity/rejection")
        need(rejected or (vv is not None and not vv.valid) or multi or explicit, "crossing widths must be invalid/uncertain or multi-branch/ambiguous")

    elif name == "vertical_interference_stripes":
        need(res.masks.get("interference") is not None and res.masks["interference"].any(), "interference must be detected")
        inter = res.masks["interference"]
        for cl in res.centerlines:
            if not cl.points_rc:
                continue
            on_stripe = sum(1 for r, c in cl.points_rc if inter[r, c]) / max(len(cl.points_rc), 1)
            need(on_stripe < 0.7, f"branch {cl.branch_id} is mostly interference stripe")

    elif name == "full_height_stripe_clutter":
        need(res.masks.get("interference") is not None and res.masks["interference"].any(), "interference must be detected")
        level = _f(res, "v2_interference_level")
        tr = _f(res, "v2_trace_pixel_fraction")
        no_conf = (
            (tr is not None and not tr.valid)
            or (level is not None and level.value in ("dominant", "prevents_assessment"))
            or res.oversegmentation_suspected
            or len(res.centerlines) == 0
        )
        need(no_conf, "must not emit confident ionospheric trace under full-height clutter")

    elif name == "partial_missing_trace":
        tr = _f(res, "v2_trace_pixel_fraction")
        cont = _f(res, "v2_trace_continuity")
        need(tr is not None and (tr.valid or bool(tr.reason_invalid)), "trace measurement must exist")
        need(cont is not None and cont.value is not None, "continuity must be reported")
        thin_c = _f(thin_horiz, "v2_trace_continuity")
        # Pair against sloping thin (same family as partial_missing)
        thin_slope = run_feature_pipeline_v2(generate_geometry_case("thin_sloping_ridge"))
        thin_c = _f(thin_slope, "v2_trace_continuity")
        gap = float(np.mean([c.gap_fraction for c in res.centerlines])) if res.centerlines else 0.0
        split = len(res.centerlines) >= 2
        lower_cont = (
            cont is not None and cont.valid and thin_c is not None and thin_c.valid
            and float(cont.value) < float(thin_c.value) - 0.05
        )
        need(gap > 0.05 or split or lower_cont, f"gap behavior not reflected (gap={gap}, branches={len(res.centerlines)})")

    elif name == "isolated_bright_impulses":
        need(res.masks.get("impulses") is not None and res.masks["impulses"].any(), "impulses must be detected")
        if res.masks.get("impulses") is not None and res.masks.get("trace_accepted") is not None:
            need(not (res.masks["impulses"] & res.masks["trace_accepted"]).any(), "impulses must not remain in accepted trace")
        impulses = res.masks.get("impulses")
        accepted = res.masks.get("trace_accepted")
        if impulses is not None and accepted is not None:
            non_impulse_accepted = int((accepted & ~impulses).sum())
            need(non_impulse_accepted > 0 or len(res.centerlines) == 0, "false trace from impulses only")

    elif name in ("zero_frame", "saturated_frame"):
        need(res.quality_status == "not_assessable", f"quality must be not_assessable, got {res.quality_status}")

    else:
        reasons.append(f"no strict criteria for {name}")

    return (len(reasons) == 0), reasons


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Preserve provenance pointer to prior version evidence
    (OUT / "PROVENANCE.md").write_text(
        f"# Synthetic geometry evidence\n\nfeature_version: `{FEATURE_VERSION}`\n"
        "Prior iml2-0.1.0 evidence preserved under docs/_phase4b1_synthetic_geometry/\n",
        encoding="utf-8",
    )
    baselines = {
        k: run_feature_pipeline_v2(generate_geometry_case(k))
        for k in (
            "thin_diagonal_baseline",
            "thin_horizontal_ridge",
            "thin_steep_baseline",
            "thin_shallow_baseline",
        )
    }
    thin_horiz = baselines["thin_horizontal_ridge"]
    rows = []
    fails = 0
    for name in GEOMETRY_CASES:
        frame = generate_geometry_case(name)
        res = run_feature_pipeline_v2(frame)
        ok, reasons = evaluate(name, res, baselines)
        if not ok:
            fails += 1
        dest = OUT / name
        dest.mkdir(exist_ok=True)
        payload = res.to_serializable()
        payload["feature_version"] = res.feature_version
        (dest / "features.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        rows.append({
            "case": name,
            "pass": ok,
            "reasons": reasons,
            "quality": res.quality_status,
            "branches": len(res.centerlines),
            "overseg": res.oversegmentation_suspected,
            "feature_version": res.feature_version,
            "fixed_H": _val(_f(res, "v2_fixed_horizontal_axis_width_bins")),
            "fixed_V": _val(_f(res, "v2_fixed_vertical_axis_width_bins")),
            "true_H_resid": _val(_f(res, "v2_true_slope_compensated_horizontal_residual_bins")),
            "h_applicable_frac": _val(_f(res, "v2_horizontal_axis_width_applicable_fraction")),
            "axis_tangent_rej": _val(_f(res, "v2_axis_tangent_rejection_count")),
        })
    report = {
        "feature_version": FEATURE_VERSION,
        "n_cases": len(rows),
        "n_pass": sum(1 for r in rows if r["pass"]),
        "n_fail": fails,
        "cases": rows,
        "thin_horizontal_H_after": {
            "true_H_resid": _val(_f(thin_horiz, "v2_true_slope_compensated_horizontal_residual_bins")),
            "fixed_H_valid": bool(_f(thin_horiz, "v2_fixed_horizontal_axis_width_bins") and _f(thin_horiz, "v2_fixed_horizontal_axis_width_bins").valid),
            "h_applicable_frac": _val(_f(thin_horiz, "v2_horizontal_axis_width_applicable_fraction")),
            "axis_tangent_rej": _val(_f(thin_horiz, "v2_axis_tangent_rejection_count")),
            "note": "Before 4B.3: true_slope_compensated_horizontal_residual ≈ 8.8 bins (invalid as low-width evidence)",
        },
    }
    (OUT / "synthetic_geometry_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        f"# Synthetic Geometry Report (Phase 4B.3 — `{FEATURE_VERSION}`)",
        "",
        f"Cases: {len(rows)}  Pass: {report['n_pass']}  Fail: {fails}",
        "",
        "| Case | Pass | H | V | Notes |",
        "|---|:---:|---:|---:|---|",
    ]
    for r in rows:
        md.append(
            f"| `{r['case']}` | {'PASS' if r['pass'] else 'FAIL'} | {r['fixed_H']} | {r['fixed_V']} | "
            f"{'; '.join(r['reasons']) or 'ok'} |"
        )
    (OUT / "SYNTHETIC_GEOMETRY_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{'FAIL' if fails else 'OK'} synthetic_geometry {report['n_pass']}/{len(rows)} version={FEATURE_VERSION}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
