#!/usr/bin/env python3
"""Reproducible full-file performance evidence orchestrator (Phase 4B.3).

Stages (exact order):
  1. cancel run (--cancel-after 30)
  2. resume run (--resume)
  3. completed run (finish remaining / ensure 1440)
  4. second pass (--second-run; counts resume-state skips separately)
  5. final report aggregation

Does not label checkpoint skips as feature-cache hits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERF_SCRIPT = ROOT / "scripts" / "run_feature_pipeline_v2_fullfile_perf.py"
DEFAULT_OUT = ROOT / "docs" / "_phase4b3_iml2-0.2.0_fullfile_perf"
DEFAULT_MAT = Path(
    r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], stage: str) -> dict:
    t0 = time.perf_counter()
    start = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    end = datetime.now(timezone.utc).isoformat()
    return {
        "stage": stage,
        "command": cmd,
        "returncode": proc.returncode,
        "wall_time_s": elapsed,
        "start_utc": start,
        "end_utc": end,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mat", type=Path, default=DEFAULT_MAT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-frames", type=int, default=1440)
    ap.add_argument("--cancel-after", type=int, default=30)
    ap.add_argument("--skip-full", action="store_true", help="Skip long full-file stages (CI smoke)")
    args = ap.parse_args()
    out = args.out
    if out.exists():
        # Fresh evidence directory for this feature version
        import shutil

        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(ROOT / "src"))
    from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION

    py = sys.executable
    base = [py, str(PERF_SCRIPT), "--mat", str(args.mat), "--out", str(out), "--max-frames", str(args.max_frames)]
    stages = []

    # 1. cancel
    stages.append(_run(base + ["--cancel-after", str(args.cancel_after)], "1_cancel"))
    # 2. resume
    stages.append(_run(base + ["--resume"], "2_resume"))
    # 3. completed (resume again if needed to finish)
    if not args.skip_full:
        stages.append(_run(base + ["--resume"], "3_completed"))
    # 4. second pass
    stages.append(_run(base + ["--resume", "--second-run"], "4_second_pass"))

    state_path = out / "perf_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    report_path = out / "fullfile_performance_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}

    timings = state.get("timings_s") or []
    final = {
        "feature_version": FEATURE_VERSION,
        "orchestrator": "run_feature_pipeline_v2_perf_orchestrator.py",
        "script_sha256": _sha256(PERF_SCRIPT),
        "orchestrator_sha256": _sha256(Path(__file__)),
        "stages": stages,
        "commands": [s["command"] for s in stages],
        "wall_time_by_stage_s": {s["stage"]: s["wall_time_s"] for s in stages},
        "sum_frame_computation_times_s": float(sum(timings)) if timings else None,
        "resume_state_skips": int(state.get("resume_state_skips", state.get("checkpoint_skips", 0))),
        "true_feature_cache_hits": int(state.get("true_feature_cache_hits", 0)),
        "source_frame_cache_hits": int(state.get("source_frame_cache_hits", 0)),
        "checkpoint_skips_not_feature_cache": int(state.get("cache_hits", 0)),
        "recomputed_frames": int(state.get("cache_misses", 0)),
        "note_on_cache": (
            "perf_state completed_frames skips are checkpoint/resume skips, "
            "NOT Feature Pipeline V2 result-cache hits. true_feature_cache_hits remains 0 "
            "unless a V2 result cache is introduced."
        ),
        "performance_report": report,
        "input_sha": report.get("source_sha_before") or report.get("source_sha_after"),
        "output_report_sha256": _sha256(report_path) if report_path.is_file() else None,
        "start_utc": stages[0]["start_utc"] if stages else None,
        "end_utc": stages[-1]["end_utc"] if stages else None,
    }
    (out / "run_manifest.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    # Merge key fields into the performance report for packaging completeness
    report.update(
        {
            "feature_version": FEATURE_VERSION,
            "orchestrator_manifest": "run_manifest.json",
            "sum_frame_computation_times_s": final["sum_frame_computation_times_s"],
            "wall_time_by_stage_s": final["wall_time_by_stage_s"],
            "resume_state_skips": final["checkpoint_skips_not_feature_cache"],
            "true_feature_cache_hits": final["true_feature_cache_hits"],
            "source_frame_cache_hits": final["source_frame_cache_hits"],
            "recomputed_frames": final["recomputed_frames"],
            "cache_semantics": final["note_on_cache"],
            "cancellation_test": {
                "cancel_after": args.cancel_after,
                "stage": "1_cancel",
            },
            "resume_test": {"stage": "2_resume"},
            "second_pass_test": {"stage": "4_second_pass"},
        }
    )
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "feature_version": FEATURE_VERSION,
        "out": str(out),
        "stages_ok": all(s["returncode"] == 0 for s in stages),
        "frames_completed": report.get("frames_completed"),
        "sum_frame_s": final["sum_frame_computation_times_s"],
        "checkpoint_skips": final["checkpoint_skips_not_feature_cache"],
        "true_feature_cache_hits": final["true_feature_cache_hits"],
    }, indent=2))
    return 0 if all(s["returncode"] == 0 for s in stages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
