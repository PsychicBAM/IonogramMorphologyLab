#!/usr/bin/env python3
"""Export full per-frame diagnostic packages for Phase 4B.1 real-frame audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
from ionogram_morphology_lab.utils.hashing import sha256_file

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

DEFAULT_MATS = {
    "Am_all_2013-01-01.mat": Path(
        r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat"
    ),
    "Am_all_2014-09-25.mat": Path(
        r"E:\ionog\conference_presentation\ion2014\maps201409sep\data\Am_all_2014-09-25.mat"
    ),
    "Am_all_2014-10-15.mat": Path(
        r"E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat"
    ),
}

# Daily samples + evening window on 2014-10-15
DEFAULT_FRAMES = {
    "Am_all_2013-01-01.mat": [1, 421, 720, 1000, 1440],
    "Am_all_2014-09-25.mat": [1, 421, 720, 1000, 1440],
    "Am_all_2014-10-15.mat": [1, 421, 720, 1000, 1201, 1300, 1431, 1440],
}


def _sha_arr(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _save_png(path: Path, arr: np.ndarray, *, cmap: str = "viridis", overlay: np.ndarray | None = None) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap)
    if overlay is not None:
        ov = np.ma.masked_where(~overlay.astype(bool), overlay.astype(float))
        ax.imshow(ov, origin="lower", aspect="auto", cmap="autumn", alpha=0.55)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0.1)
    fig.savefig(path)
    plt.close(fig)


def _mask_png(path: Path, mask: np.ndarray, raw: np.ndarray) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.imshow(raw, origin="lower", aspect="auto", cmap="gray")
    ov = np.ma.masked_where(~mask.astype(bool), mask.astype(float))
    ax.imshow(ov, origin="lower", aspect="auto", cmap="cool", alpha=0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0.1)
    fig.savefig(path)
    plt.close(fig)


def _width_dir_png(path: Path, raw: np.ndarray, points, direction: str, n_r: float = 0, n_c: float = 1) -> None:
    if plt is None or not points:
        return
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.imshow(raw, origin="lower", aspect="auto", cmap="gray")
    sample = points[:: max(1, len(points) // 12)]
    for r0, c0 in sample:
        if direction == "vertical":
            ax.plot([c0, c0], [r0 - 12, r0 + 12], color="cyan", lw=0.8)
        elif direction == "horizontal":
            ax.plot([c0 - 12, c0 + 12], [r0, r0], color="lime", lw=0.8)
        else:
            ax.plot(
                [c0 - 10 * n_c, c0 + 10 * n_c],
                [r0 - 10 * n_r, r0 + 10 * n_r],
                color="magenta",
                lw=0.8,
            )
    ax.set_title(direction, fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0.2)
    fig.savefig(path)
    plt.close(fig)


def export_frame(
    dest: Path,
    *,
    mat_path: Path,
    frame: np.ndarray,
    frame_index: int,
    source_sha: str,
    mapped_time: str,
) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    v2 = run_feature_pipeline_v2(
        frame,
        signal_contract_id="kfu_amp_all_v1",
        profile_id="kfu_cyclone_2013_2014",
        frame_index=frame_index,
        source_mat_sha256=source_sha,
    )
    raw_sha = _sha_arr(frame)
    identity = {
        "source_path": str(mat_path),
        "source_sha256": source_sha,
        "frame": frame_index,
        "mapped_time": mapped_time,
        "profile": "kfu_cyclone_2013_2014",
        "signal_contract": "kfu_amp_all_v1",
        "feature_version": FEATURE_VERSION,
        "raw_frame_sha256": raw_sha,
        "axes_status": "not_supplied_bin_indices_only",
        "interpretation": "automatic diagnostic; owner review pending",
        "oversegmentation_suspected": v2.oversegmentation_suspected,
    }
    (dest / "identity.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
    np.save(dest / "raw.npy", frame)
    _save_png(dest / "raw.png", frame, cmap="gray")

    score = v2.representations.get("signal_background_score")
    if score is not None and score.array is not None:
        _save_png(dest / "diagnostic_normalized.png", score.array, cmap="magma")
    else:
        _save_png(dest / "diagnostic_normalized.png", frame, cmap="magma")

    masks = v2.masks
    mapping = {
        "candidate_trace_mask": "trace_candidate",
        "candidate_before_exclusion_mask": "trace_candidate_before_exclusion",
        "accepted_trace_mask": "trace_accepted",
        "interference_mask": "interference",
        "background_mask": "background",
        "uncertain_mask": "uncertain",
        "excluded_mask": "excluded",
        "floor_clutter_mask": "floor_clutter",
        "impulse_mask": "impulses",
    }
    for out_name, key in mapping.items():
        m = masks.get(key)
        if m is None:
            m = np.zeros_like(frame, dtype=bool)
        np.save(dest / f"{out_name}.npy", m.astype(np.uint8))
        _mask_png(dest / f"{out_name}.png", m, frame)
    # Accepted nonfloor convenience
    accepted = masks.get("trace_accepted")
    floor = masks.get("floor_clutter")
    if accepted is not None and floor is not None:
        nonfloor = accepted & (~floor)
        np.save(dest / "accepted_nonfloor_trace_mask.npy", nonfloor.astype(np.uint8))
        _mask_png(dest / "accepted_nonfloor_trace_mask.png", nonfloor, frame)

    before = masks.get("centerlines_before")
    after = masks.get("centerlines_after")
    if before is not None:
        _mask_png(dest / "centerlines_before_consolidation.png", before, frame)
    if after is not None:
        _mask_png(dest / "centerlines_after_consolidation.png", after, frame)

    bl = masks.get("branch_labels")
    if bl is not None and plt is not None:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
        ax.imshow(frame, origin="lower", aspect="auto", cmap="gray")
        ax.imshow(np.ma.masked_where(bl == 0, bl), origin="lower", aspect="auto", cmap="tab20", alpha=0.55)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout(pad=0.1)
        fig.savefig(dest / "branch_labels.png")
        plt.close(fig)

    for key, fname in (
        ("vertical_width_map", "vertical_width_map"),
        ("horizontal_width_map", "horizontal_width_map"),
        ("normal_to_ridge_width_map", "normal_to_ridge_width_map"),
        ("fixed_horizontal_width_map", "fixed_horizontal_width_map"),
    ):
        wm = masks.get(key)
        if wm is None:
            continue
        if key.endswith("_map") and "normal" not in key and "fixed_horizontal" not in key or key == "vertical_width_map":
            np.save(dest / f"{fname}.npy", wm)
        if key in ("vertical_width_map", "horizontal_width_map"):
            np.save(dest / f"{fname}.npy", wm)
        if plt is not None:
            fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
            ax.imshow(frame, origin="lower", aspect="auto", cmap="gray")
            ax.imshow(wm, origin="lower", aspect="auto", cmap="plasma", alpha=0.65)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.tight_layout(pad=0.1)
            fig.savefig(dest / f"{fname}.png")
            plt.close(fig)

    # Direction overlays
    pts = v2.centerlines[0].points_rc if v2.centerlines else []
    slope = v2.centerlines[0].slope if v2.centerlines else 0.0
    tang = float(np.hypot(slope, 1.0)) + 1e-9
    _width_dir_png(dest / "vertical_width_direction.png", frame, pts, "vertical")
    _width_dir_png(dest / "horizontal_width_direction.png", frame, pts, "horizontal")
    _width_dir_png(
        dest / "normal_to_ridge_width_direction.png",
        frame,
        pts,
        "normal_to_ridge",
        n_r=-1.0 / tang,
        n_c=slope / tang,
    )

    if plt is not None:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
        ax.imshow(frame, origin="lower", aspect="auto", cmap="gray")
        if after is not None:
            ax.imshow(np.ma.masked_where(~after, after.astype(float)), origin="lower", aspect="auto", cmap="autumn", alpha=0.5)
        ax.set_title("temporal_overlay_placeholder", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout(pad=0.1)
        fig.savefig(dest / "temporal_overlay.png")
        plt.close(fig)

    (dest / "features.json").write_text(
        json.dumps(v2.to_serializable(), indent=2, default=str), encoding="utf-8"
    )
    (dest / "component_decisions.json").write_text(
        json.dumps(v2.component_decisions, indent=2, default=str), encoding="utf-8"
    )
    # Per-branch H/V validity summary for owner review
    (dest / "branch_width_summary.json").write_text(
        json.dumps(
            {
                "feature_version": FEATURE_VERSION,
                "axis_tangent_rejection_count": (
                    v2.features.get("v2_axis_tangent_rejection_count").value
                    if v2.features.get("v2_axis_tangent_rejection_count")
                    else None
                ),
                "multiple_intersection_rejection_count": (
                    v2.features.get("v2_multiple_intersection_rejection_count").value
                    if v2.features.get("v2_multiple_intersection_rejection_count")
                    else None
                ),
                "branch_overlap_rejection_count": (
                    v2.features.get("v2_branch_overlap_rejection_count").value
                    if v2.features.get("v2_branch_overlap_rejection_count")
                    else None
                ),
                "horizontal_applicable_fraction": (
                    v2.features.get("v2_horizontal_axis_width_applicable_fraction").value
                    if v2.features.get("v2_horizontal_axis_width_applicable_fraction")
                    else None
                ),
                "vertical_applicable_fraction": (
                    v2.features.get("v2_vertical_axis_width_applicable_fraction").value
                    if v2.features.get("v2_vertical_axis_width_applicable_fraction")
                    else None
                ),
                "branch_records": v2.branch_records,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return {
        "frame": frame_index,
        "preconsolidation_centerline_count": (
            v2.features.get("v2_preconsolidation_centerline_count").value
            if v2.features.get("v2_preconsolidation_centerline_count")
            else None
        ),
        "total_connected_component_count": (
            v2.features.get("v2_total_connected_component_count").value
            if v2.features.get("v2_total_connected_component_count")
            else None
        ),
        "floor_rejected_component_count": (
            v2.features.get("v2_floor_rejected_component_count").value
            if v2.features.get("v2_floor_rejected_component_count")
            else None
        ),
        "accepted_nonfloor_trace_fraction": (
            v2.features.get("v2_accepted_nonfloor_trace_fraction").value
            if v2.features.get("v2_accepted_nonfloor_trace_fraction")
            else None
        ),
        "consolidated": (
            v2.features.get("v2_consolidated_branch_count").value
            if v2.features.get("v2_consolidated_branch_count")
            else None
        ),
        "oversegmentation_suspected": v2.oversegmentation_suspected,
        "elapsed_s": v2.elapsed_s,
        "quality": v2.quality_status,
    }


def contact_sheet(out_png: Path, frame_dirs: list[Path]) -> None:
    if plt is None or not frame_dirs:
        return
    n = len(frame_dirs)
    cols = (
        "raw.png",
        "candidate_before_exclusion_mask.png",
        "floor_clutter_mask.png",
        "interference_mask.png",
        "accepted_nonfloor_trace_mask.png",
        "centerlines_after_consolidation.png",
        "vertical_width_direction.png",
        "horizontal_width_direction.png",
        "vertical_width_map.png",
        "fixed_horizontal_width_map.png",
    )
    titles = ["raw", "cand-pre", "floor", "interf", "accepted", "centerlines", "V-dir", "H-dir", "V-map", "H-map"]
    fig, axes = plt.subplots(n, len(cols), figsize=(2.2 * len(cols), 2.0 * n), dpi=100)
    if n == 1:
        axes = np.array([axes])
    for i, d in enumerate(frame_dirs):
        for j, name in enumerate(cols):
            ax = axes[i, j]
            p = d / name
            if p.is_file():
                ax.imshow(plt.imread(p))
            ax.set_xticks([])
            ax.set_yticks([])
            if i == 0:
                ax.set_title(titles[j], fontsize=7)
            if j == 0:
                ax.set_ylabel(d.name, fontsize=6)
    fig.suptitle("Contact sheet — automatic diagnostic; owner review pending (not owner-reviewed)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "_phase4b3_iml2-0.2.0_diagnostics",
    )
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    review_rows = []
    t0 = time.perf_counter()
    for mat_name, frames in DEFAULT_FRAMES.items():
        mat = DEFAULT_MATS[mat_name]
        if not mat.is_file():
            summary.append({"mat": mat_name, "status": "missing"})
            continue
        sha = sha256_file(mat)
        amp = load_amplitude_matrix(mat, variable="Amp_all").data
        frame_dirs = []
        for fi in frames:
            frame, _ = extract_frame_consistent(amp, fi, height_bins=256, frequency_bins=400)
            # mapped time: minute-of-day approximation for 1440 daily files
            hh = (fi - 1) // 60
            mm = (fi - 1) % 60
            mapped = f"{hh:02d}:{mm:02d}"
            dest = out / mat.stem / f"frame_{fi:04d}"
            info = export_frame(
                dest,
                mat_path=mat,
                frame=frame,
                frame_index=fi,
                source_sha=sha,
                mapped_time=mapped,
            )
            info["mat"] = mat_name
            # Floor false-trace statistics
            feats = json.loads((dest / "features.json").read_text(encoding="utf-8")).get("features", {})
            info["floor_rejected"] = (feats.get("v2_floor_rejected_component_count") or {}).get("value")
            info["nonfloor_frac"] = (feats.get("v2_accepted_nonfloor_trace_fraction") or {}).get("value")
            info["preconsol"] = (feats.get("v2_preconsolidation_centerline_count") or {}).get("value")
            summary.append(info)
            frame_dirs.append(dest)
            review_rows.append(
                {
                    "mat": mat_name,
                    "frame": fi,
                    "feature_version": FEATURE_VERSION,
                    "trace_mask_acceptable": "",
                    "floor_rejection_acceptable": "",
                    "interference_mask_acceptable": "",
                    "centerlines_reasonable": "",
                    "branch_separation_reasonable": "",
                    "h_axis_measurement_direction_correct": "",
                    "v_axis_measurement_direction_correct": "",
                    "branch_overlap_handled_correctly": "",
                    "final_geometry_acceptable_for_rule_development": "",
                    "comments": "",
                    "status": "owner review pending",
                    "automatic_diagnostic": True,
                    "total_connected_component_count": info.get("total_connected_component_count"),
                    "preconsolidation_centerline_count": info.get("preconsolidation_centerline_count"),
                    "floor_rejected_component_count": info.get("floor_rejected_component_count"),
                    "accepted_nonfloor_trace_fraction": info.get("accepted_nonfloor_trace_fraction"),
                    "consolidated": info["consolidated"],
                    "oversegmentation_suspected": info["oversegmentation_suspected"],
                }
            )
        contact_sheet(out / mat.stem / "contact_sheet.png", frame_dirs)

    (out / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "owner_geometry_review_table.json").write_text(
        json.dumps(
            {
                "phase": "4B.3",
                "feature_version": FEATURE_VERSION,
                "note": (
                    "Geometry review only — not morphology ground truth. "
                    "Not owner-reviewed until fields completed. "
                    "Phase 4C blocked until synthetic H/V independence, parallel-branch "
                    "contamination, version bump, and owner review of representative frames."
                ),
                "rows": review_rows,
                "completed": 0,
                "pending": len(review_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Human CSV
    csv_lines = [
        "mat,frame,feature_version,trace_mask_acceptable,floor_rejection_acceptable,"
        "interference_mask_acceptable,centerlines_reasonable,branch_separation_reasonable,"
        "h_axis_measurement_direction_correct,v_axis_measurement_direction_correct,"
        "branch_overlap_handled_correctly,final_geometry_acceptable_for_rule_development,"
        "comments,status,total_connected_component_count,preconsolidation_centerline_count,"
        "floor_rejected_component_count,accepted_nonfloor_trace_fraction,"
        "consolidated,oversegmentation_suspected"
    ]
    for r in review_rows:
        csv_lines.append(
            f"{r['mat']},{r['frame']},{r['feature_version']},,,,,,,,,"
            f",owner review pending,"
            f"{r['total_connected_component_count']},{r['preconsolidation_centerline_count']},"
            f"{r['floor_rejected_component_count']},{r['accepted_nonfloor_trace_fraction']},"
            f"{r['consolidated']},{r['oversegmentation_suspected']}"
        )
    (out / "owner_geometry_review_table.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    md = [
        f"# Feature Pipeline V2 — Real-Frame Diagnostic Audit (Phase 4B.3 / `{FEATURE_VERSION}`)",
        "",
        "Synthetic geometry tests + automatic real-frame shadow audit; **owner review pending.**",
        "",
        "No morphology ground truth was assigned automatically.",
        "Owner review begins only after obvious floor false positives are removed.",
        "",
        f"Exported frames: {len(review_rows)}",
        f"Elapsed: {time.perf_counter() - t0:.1f}s",
        "",
        "| MAT | Frame | Total CC | Preconsol | Floor rej | Nonfloor frac | Consolidated | Overseg |",
        "|-----|------:|---------:|----------:|----------:|--------------:|-------------:|:-------:|",
    ]
    for s in summary:
        if "frame" not in s:
            continue
        md.append(
            f"| `{s['mat']}` | {s['frame']} | {s.get('total_connected_component_count')} | "
            f"{s.get('preconsolidation_centerline_count')} | {s.get('floor_rejected_component_count')} | "
            f"{s.get('accepted_nonfloor_trace_fraction')} | {s['consolidated']} | "
            f"{'yes' if s['oversegmentation_suspected'] else 'no'} |"
        )
    (out / "REAL_FRAME_SHADOW_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Exported", len(review_rows), "frames to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
