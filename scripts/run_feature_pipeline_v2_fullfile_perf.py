#!/usr/bin/env python3
"""Full-file V2 shadow performance with process RSS, cancel, resume, cache evidence."""
from __future__ import annotations

import argparse
import json
import os
import time
import tracemalloc
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

DEFAULT_MAT = Path(
    r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat"
)


def _rss_mb() -> float | None:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        pass
    # Windows working set via ctypes
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
        GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return float(counters.WorkingSetSize) / (1024 * 1024)
    except Exception:
        pass
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mat", type=Path, default=DEFAULT_MAT)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "_phase4b3_iml2-0.2.0_fullfile_perf")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-frames", type=int, default=1440)
    ap.add_argument("--cancel-after", type=int, default=0, help="If >0, cancel after N newly processed frames")
    ap.add_argument("--second-run", action="store_true", help="Measure resume-state skips on already-completed frames")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "perf_state.json"

    rss_baseline = _rss_mb()
    rss_peak = rss_baseline

    state = {
        "feature_version": FEATURE_VERSION,
        "completed_frames": [],
        "timings_s": [],
        "mem_mb_samples": [],
        "failed": [],
        "invalid": [],
        "cache_hits": 0,  # legacy name: resume-state / checkpoint skips (NOT feature-cache hits)
        "cache_misses": 0,  # recomputed frames
        "true_feature_cache_hits": 0,
        "source_frame_cache_hits": 0,
        "resume_state_skips": 0,
        "cancelled": False,
        "quality_counts": {"assessable": 0, "degraded": 0, "interference_limited": 0, "not_assessable": 0},
        "overseg_count": 0,
    }
    if args.resume and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        prev_ver = state.get("feature_version")
        if prev_ver and prev_ver != FEATURE_VERSION:
            print(
                f"FAIL feature_version mismatch in perf_state: {prev_ver} != {FEATURE_VERSION}. "
                "Refuse to mix iml2 versions; delete state or use a new --out directory."
            )
            return 2
        state["feature_version"] = FEATURE_VERSION
        state.setdefault("quality_counts", {"assessable": 0, "degraded": 0, "interference_limited": 0, "not_assessable": 0})
        state.setdefault("overseg_count", 0)
        state.setdefault("true_feature_cache_hits", 0)
        state.setdefault("source_frame_cache_hits", 0)
        state.setdefault("resume_state_skips", 0)
        # Resume continues a cancelled run unless a new cancel-after is requested
        if not args.cancel_after:
            state["cancelled"] = False

    if not args.mat.is_file():
        print("FAIL missing mat", args.mat)
        return 1

    sha_before = sha256_file(args.mat)
    # Measure RSS after source load separately
    loaded = load_amplitude_matrix(args.mat, variable="Amp_all")
    amp = loaded.data
    rss_after_source = _rss_mb()
    if rss_after_source is not None:
        rss_peak = max(rss_peak or 0, rss_after_source)
    source_matrix_nbytes = int(getattr(amp, "nbytes", 0))

    n = min(int(amp.shape[0]) if amp.ndim >= 1 else args.max_frames, args.max_frames)
    # Amp_all is typically [frames, height, freq] or similar — extract_frame_consistent handles it
    tracemalloc.start()
    t_all0 = time.perf_counter()
    done = set(state["completed_frames"])
    newly = 0
    cancelled = False

    def cancel_check() -> bool:
        return cancelled

    for fi in range(1, n + 1):
        if fi in done:
            state["cache_hits"] += 1  # checkpoint / resume-state skip
            state["resume_state_skips"] = int(state.get("resume_state_skips", 0)) + 1
            if args.second_run:
                continue
            continue
        if args.second_run:
            # second run only counts resume-state skips
            continue
        state["cache_misses"] += 1  # recomputed
        if args.cancel_after and newly >= args.cancel_after:
            cancelled = True
            state["cancelled"] = True
            break
        t0 = time.perf_counter()
        try:
            frame, _ = extract_frame_consistent(amp, fi, height_bins=256, frequency_bins=400)
            res = run_feature_pipeline_v2(
                frame,
                signal_contract_id="kfu_amp_all_v1",
                profile_id="kfu_cyclone_2013_2014",
                frame_index=fi,
                source_mat_sha256=sha_before,
                cancel_check=cancel_check,
            )
            if cancelled or "cancelled" in res.notes:
                state["cancelled"] = True
                break
            q = res.quality_status
            state["quality_counts"][q] = state["quality_counts"].get(q, 0) + 1
            if q == "not_assessable":
                state["invalid"].append(fi)
            if res.oversegmentation_suspected:
                state["overseg_count"] += 1
            compact = {
                "frame": fi,
                "quality": q,
                "preconsol": (res.features.get("v2_preconsolidation_centerline_count") or type("X", (), {"value": None})).value,
                "consolidated": (res.features.get("v2_consolidated_branch_count") or type("X", (), {"value": None})).value,
                "overseg": res.oversegmentation_suspected,
                "elapsed_s": res.elapsed_s,
            }
            (out / "per_frame").mkdir(exist_ok=True)
            (out / "per_frame" / f"frame_{fi:04d}.json").write_text(json.dumps(compact), encoding="utf-8")
            state["completed_frames"].append(fi)
            newly += 1
        except Exception as exc:  # noqa: BLE001
            state["failed"].append({"frame": fi, "error": str(exc)})
            # failed frames are NOT counted as completed
        elapsed = time.perf_counter() - t0
        state["timings_s"].append(elapsed)
        cur_rss = _rss_mb()
        if cur_rss is not None:
            rss_peak = max(rss_peak or 0, cur_rss)
        cur_t, peak_t = tracemalloc.get_traced_memory()
        if fi % 60 == 0 or fi == 1:
            state["mem_mb_samples"].append(
                {
                    "frame": fi,
                    "tracemalloc_current_mb": cur_t / (1024 * 1024),
                    "tracemalloc_peak_mb": peak_t / (1024 * 1024),
                    "process_rss_mb": cur_rss,
                }
            )
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    total_elapsed = time.perf_counter() - t_all0
    _, peak_t = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sha_after = sha256_file(args.mat)
    times = np.asarray(state["timings_s"], dtype=float)
    out_size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    report = {
        "mat": str(args.mat),
        "feature_version": FEATURE_VERSION,
        "frames_requested": n,
        "frames_completed": len(state["completed_frames"]),
        "total_elapsed_s": total_elapsed,
        "median_s_per_frame": float(np.median(times)) if times.size else None,
        "p95_s_per_frame": float(np.percentile(times, 95)) if times.size else None,
        "process_rss_baseline_mb": rss_baseline,
        "process_rss_after_source_load_mb": rss_after_source,
        "process_rss_peak_mb": rss_peak,
        "source_matrix_nbytes": source_matrix_nbytes,
        "source_matrix_mb": source_matrix_nbytes / (1024 * 1024),
        "python_tracemalloc_peak_mb": peak_t / (1024 * 1024),
        "memory_at_intervals": state["mem_mb_samples"],
        "compact_benchmark_output_size_bytes": out_size,
        "output_size_note": "Compact per-frame JSON benchmark only — not a complete diagnostic export",
        "cancellation": state["cancelled"],
        "cancel_after_requested": args.cancel_after,
        "resume_supported": True,
        "cache_hits": state["cache_hits"],
        "cache_misses": state["cache_misses"],
        "resume_state_skips": state.get("resume_state_skips", state["cache_hits"]),
        "true_feature_cache_hits": state.get("true_feature_cache_hits", 0),
        "source_frame_cache_hits": state.get("source_frame_cache_hits", 0),
        "recomputed_frames": state["cache_misses"],
        "cache_semantics": (
            "cache_hits/resume_state_skips count frames already in perf_state.completed_frames; "
            "they are NOT Feature Pipeline V2 feature-result cache hits."
        ),
        "source_sha_before": sha_before,
        "source_sha_after": sha_after,
        "source_unchanged": sha_before == sha_after,
        "failed_frame_count": len(state["failed"]),
        "invalid_frame_count": len(state["invalid"]),
        "quality_counts": state["quality_counts"],
        "oversegmentation_suspected_count": state["overseg_count"],
        "failed": state["failed"][:50],
    }
    (out / "fullfile_performance_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "frames_completed", "total_elapsed_s", "median_s_per_frame", "p95_s_per_frame",
        "process_rss_peak_mb", "python_tracemalloc_peak_mb", "cancellation", "cache_hits", "cache_misses",
        "quality_counts", "oversegmentation_suspected_count",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
