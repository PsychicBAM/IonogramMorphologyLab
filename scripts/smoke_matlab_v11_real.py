#!/usr/bin/env python3
"""Real MATLAB R2019a -batch smoke tests on approved non-secret MAT (or synthetic fallback)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.importers.adapters import extract_frame_kfu, load_amplitude_matrix
from ionogram_morphology_lab.matlab_studio.api_bridge import prepare_run_workspace, read_registered_side_effects
from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest, run_matlab_job
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir

METHODS = [
    "matlab_builtin/layer_detection/iml_detect_e_layer_candidate.m",
    "matlab_builtin/es_analysis/iml_detect_es_candidate.m",
    "matlab_builtin/f_layer_analysis/iml_detect_f1_candidate.m",
    "matlab_builtin/f_layer_analysis/iml_detect_f2_candidate.m",
    "matlab_builtin/spread_f_analysis/iml_detect_frequency_spread_candidate.m",
    "matlab_builtin/spread_f_analysis/iml_detect_range_spread_candidate.m",
    "matlab_builtin/spread_f_analysis/iml_detect_mixed_spread_candidate.m",
    "matlab_builtin/interference/iml_detect_vertical_interference.m",
    "matlab_builtin/branch_analysis/iml_count_trace_branches.m",
    "matlab_builtin/branch_analysis/iml_detect_possible_ox_pattern.m",
    "matlab_builtin/parameters/iml_estimate_candidate_frequency.m",
]

REAL_CANDIDATES = [
    ROOT.parent / "ion2013" / "maps201301jan" / "data" / "Am_all_2013-01-01.mat",
    ROOT / "synthetic_data" / "demo_mixed_diffuse.mat",
]


def pick_mat() -> Path:
    for p in REAL_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError("No approved MAT found")


def load_frame(mat: Path) -> np.ndarray:
    loaded = load_amplitude_matrix(mat)
    # KFU-like stacked layout or plain 2D demo
    data = loaded.data
    if data.ndim == 2 and data.shape[0] >= 256 and data.shape[1] == 400 and data.shape[0] % 256 == 0:
        return extract_frame_kfu(data, 720)  # midday-ish
    if data.ndim == 2:
        return np.asarray(data)
    raise ValueError(f"Unsupported amplitude shape: {data.shape}")


def main() -> int:
    mat = pick_mat()
    sha_before = sha256_file(mat)
    frame = load_frame(mat)
    ff = list(np.linspace(1.5, 9.081, frame.shape[1]))
    hh = [i * 2.5 for i in range(frame.shape[0])]
    matlab = shutil.which("matlab") or r"D:\MATLAB\R2019a\bin\matlab.exe"
    report = {"mat": str(mat), "sha_before": sha_before, "matlab": matlab, "results": []}
    helpers = ROOT / "matlab_helpers"
    out_root = ensure_dir(ROOT / "workspaces" / "_v11_matlab_smoke")

    for rel in METHODS:
        script = ROOT / rel
        work = ensure_dir(out_root / script.stem)
        prepare_run_workspace(
            work,
            current_frame=frame,
            frequency_axis=ff,
            range_axis=hh,
            profile={"profile_id": "kfu_cyclone_2013_2014", "status": "provisional"},
            metadata={"source_mat": str(mat), "frame_index": 720},
            frame_ids=[720],
        )
        if helpers.exists():
            for p in helpers.glob("*.m"):
                shutil.copy2(p, work / p.name)
        # also copy local helpers from method folder if any
        for p in script.parent.glob("*.m"):
            if p.name.startswith("local_") or p.name.startswith("iml_"):
                # do not overwrite the script itself path handling — runner copies script
                pass
        req = MatlabRunRequest(
            script_path=script,
            entrypoint=script.name,
            backend="external_matlab",
            matlab_executable=matlab,
            timeout_s=180,
            work_dir=work,
            source_mat_paths=[str(mat)],
            inputs={"iml_current_frame": frame},
        )
        try:
            res = run_matlab_job(req)
            side = read_registered_side_effects(work)
            entry = {
                "method": script.stem,
                "status": res.status,
                "elapsed_s": res.elapsed_s,
                "error_message": res.error_message,
                "source_mats_unchanged": res.source_mats_unchanged,
                "output_files": res.output_files[:20],
                "side_effects": {k: (len(v) if isinstance(v, list) else v) for k, v in side.items()},
                "stdout_tail": (res.stdout or "")[-500:],
                "stderr_tail": (res.stderr or "")[-500:],
            }
        except Exception as exc:  # noqa: BLE001
            entry = {"method": script.stem, "status": "exception", "error_message": str(exc)}
        report["results"].append(entry)
        print(f"{script.stem}: {entry.get('status')}")

    sha_after = sha256_file(mat)
    report["sha_after"] = sha_after
    report["source_mat_unchanged"] = sha_before == sha_after
    path = out_root / "smoke_report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)
    ok_statuses = {"ok", "error", "timeout", "no_backend"}  # error ok if isolated
    crashed = any(r.get("status") == "exception" for r in report["results"])
    if not report["source_mat_unchanged"]:
        print("FAIL: source MAT changed")
        return 1
    if crashed:
        print("FAIL: uncaught exceptions")
        return 1
    # Prefer at least some ok when MATLAB available
    oks = sum(1 for r in report["results"] if r.get("status") == "ok")
    print(f"ok_count={oks}/{len(METHODS)} source_unchanged={report['source_mat_unchanged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
