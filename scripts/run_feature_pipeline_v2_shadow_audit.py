#!/usr/bin/env python3
"""Resumable Feature Pipeline V2 shadow audit on approved real MAT archives."""

from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame
from ionogram_morphology_lab.utils.hashing import sha256_file

DEFAULT_MATS = [
    Path(r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat"),
    Path(r"E:\ionog\conference_presentation\ion2014\maps201409sep\data\Am_all_2014-09-25.mat"),
    Path(r"E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat"),
]

# Representative MATLAB frame indices (1-based)
DEFAULT_FRAMES = [1, 421, 720, 1000, 1440]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "_shadow_audit_v2")
    ap.add_argument("--frames", type=str, default=",".join(str(x) for x in DEFAULT_FRAMES))
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    frames = [int(x) for x in args.frames.split(",") if x.strip()]
    out_root = args.out
    out_root.mkdir(parents=True, exist_ok=True)
    state_path = out_root / "audit_state.json"
    state = {"completed": [], "timings": [], "notes": []}
    if args.resume and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    report_lines = [
        "# Feature Pipeline V2 Shadow Audit",
        "",
        f"feature_version: `{FEATURE_VERSION}`",
        "",
        "All real-frame interpretations remain: **automatic diagnostic; owner review pending**",
        "",
        "No threshold tuning was performed against assumed labels.",
        "",
    ]

    peak_mem = 0.0
    tracemalloc.start()
    for mat in DEFAULT_MATS:
        if not mat.is_file():
            report_lines.append(f"- SKIP missing: `{mat}`")
            continue
        sha_before = sha256_file(mat)
        loaded = load_amplitude_matrix(mat, variable="Amp_all")
        amp = loaded.data
        # Cache amplitude in memory once per file
        for fi in frames:
            key = f"{mat.name}:{fi}"
            if key in state["completed"]:
                continue
            t0 = time.perf_counter()
            frame, _rng = extract_frame_consistent(
                amp, fi, height_bins=256, frequency_bins=400
            )
            v2 = run_feature_pipeline_v2(
                frame,
                signal_contract_id="kfu_amp_all_v1",
                profile_id="kfu_cyclone_2013_2014",
                frame_index=fi,
                source_mat_sha256=sha_before,
            )
            seg = segment_frame(frame)
            v1 = extract_features(frame, seg).to_dict()
            elapsed = time.perf_counter() - t0
            current, peak = tracemalloc.get_traced_memory()
            peak_mem = max(peak_mem, peak / (1024 * 1024))

            dest = out_root / mat.stem / f"frame_{fi:04d}"
            dest.mkdir(parents=True, exist_ok=True)
            np.save(dest / "raw_frame.npy", frame)
            for name, arr in v2.masks.items():
                np.save(dest / f"mask_{name}.npy", arr)
            (dest / "features_v2.json").write_text(
                json.dumps(v2.to_serializable(), indent=2, default=str), encoding="utf-8"
            )
            (dest / "features_v1_compare.json").write_text(
                json.dumps(v1, indent=2, default=str), encoding="utf-8"
            )
            notes = []
            q = v2.quality_status
            if q == "not_assessable":
                notes.append("unreasonable_or_abstain: not_assessable")
            h = v2.features.get("v2_median_local_horizontal_width_bins")
            if h and h.valid and float(h.value) > 40:
                notes.append("review: unusually large horizontal residual width")
            state["completed"].append(key)
            state["timings"].append({"key": key, "elapsed_s": elapsed, "quality": q})
            state["notes"].extend([f"{key}: {n}" for n in notes])
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            report_lines.append(
                f"- `{key}` quality={q} elapsed={elapsed:.3f}s centerlines={len(v2.centerlines)} "
                f"— *automatic diagnostic; owner review pending*"
            )

        sha_after = sha256_file(mat)
        if sha_after != sha_before:
            report_lines.append(f"- ERROR source MAT SHA changed for `{mat.name}`")
        else:
            report_lines.append(f"- source MAT SHA unchanged for `{mat.name}`: `{sha_before[:16]}…`")

    times = [t["elapsed_s"] for t in state["timings"]]
    mean_t = float(np.mean(times)) if times else float("nan")
    report_lines.extend(
        [
            "",
            "## Performance snapshot",
            "",
            f"- frames audited: {len(times)}",
            f"- mean time per frame: {mean_t:.3f} s",
            f"- peak traced memory (MB): {peak_mem:.1f}",
            f"- feature_version: {FEATURE_VERSION}",
            "",
            "## Notes for later correction",
            "",
        ]
    )
    if state["notes"]:
        report_lines.extend([f"- {n}" for n in state["notes"]])
    else:
        report_lines.append("- (none recorded)")

    report_lines.extend(
        [
            "",
            "## Disclaimer",
            "",
            "This audit does not claim scientific validation or improved classification accuracy.",
            "",
        ]
    )
    doc = ROOT / "docs" / "FEATURE_PIPELINE_V2_SHADOW_AUDIT.md"
    doc.write_text("\n".join(report_lines), encoding="utf-8")
    (out_root / "performance.json").write_text(
        json.dumps({"mean_s": mean_t, "peak_mb": peak_mem, "n": len(times)}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
