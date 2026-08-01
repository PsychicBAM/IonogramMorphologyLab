#!/usr/bin/env python3
"""Benchmark frame access on approved non-blinded / synthetic MAT data.

Does NOT use Article 3 blinded packages.
Prefer an external KFU Am_all_*.mat path via --mat; otherwise uses synthetic.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.importers.audit import audit_mat_path
from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.instrument_profiles.schema import load_profile, profiles_dir
from ionogram_morphology_lab.rendering.ionogram_render import RenderSpec, render_contact_sheet, render_raw_ionogram
from ionogram_morphology_lab.instrument_profiles.schema import frequency_axis_from_profile, range_axis_from_profile
from ionogram_morphology_lab.security import default_blocklist
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


def timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mat", type=str, default="", help="Approved non-blinded MAT path")
    ap.add_argument("--out", type=str, default="", help="JSON results path")
    args = ap.parse_args()

    if args.mat:
        mat = default_blocklist().assert_allowed(args.mat)
        profile = load_profile(profiles_dir() / "kfu_cyclone_2013_2014.yaml").to_dict()
    else:
        syn = app_root() / "synthetic_data"
        write_synthetic_mat_library(syn)
        mat = syn / "demo_mixed_diffuse.mat"
        profile = {
            "profile_id": "syn_bench",
            "amplitude_variable_name": "Amp_all",
            "height_bins": 256,
            "frequency_bins": 400,
            "frames_per_file": 3,
            "matrix_layout": "frames_stacked_rows",
            "profile_verification_status": "user-defined-unverified",
            "time_mapping": "matlab_index_minus_1_minute",
            "frequency_start_mhz": 1.5,
            "frequency_step_mhz": 0.019,
            "nominal_range_km_per_bin": 2.5,
            "range_axis_label_en": "Nominal virtual height",
        }

    cache_root = ensure_dir(app_root() / "workspaces" / "_bench_cache")
    store = FrameStore(mat, profile, cache_root=cache_root)
    if store.cache_dir.exists():
        store.delete_cache()

    results = {
        "mat": str(mat),
        "file_size_mb": round(mat.stat().st_size / (1024 * 1024), 3),
        "note": "Synthetic fallback used" if not args.mat else "User-provided approved MAT",
        "article3_blinded": False,
    }

    inv, dt = timed(lambda: inventory_mat(mat))
    results["metadata_audit_s"] = round(dt, 4)
    results["inventory_status"] = inv.status

    audit, dt = timed(lambda: audit_mat_path(mat, profile))
    results["audit_s"] = round(dt, 4)

    st, dt = timed(lambda: store.build_cache())
    results["first_cache_build_s"] = round(dt, 4)
    results["cache_valid"] = st.valid
    results["cache_path"] = st.path
    if st.provenance:
        results["matrix_shape"] = st.provenance.get("shape")
        results["cache_format"] = st.provenance.get("cache_format_version")

    # uncached-like: clear LRU then fetch
    store.lru.clear()
    _, dt = timed(lambda: store.get_frame(1, prefetch=False))
    results["frame_retrieval_after_clear_lru_s"] = round(dt, 4)

    _, dt = timed(lambda: store.get_frame(1, prefetch=False))
    results["cached_lru_frame_retrieval_s"] = round(dt, 4)

    from ionogram_morphology_lab.instrument_profiles.schema import InstrumentProfile

    # render
    frame = store.get_frame(1)
    out = ensure_dir(app_root() / "workspaces" / "_bench") / "frame.png"
    # build minimal profile object-like via dict axes
    freq = [1.5 + i * 0.019 for i in range(400)]
    rng = [i * 2.5 for i in range(256)]
    _, dt = timed(lambda: render_raw_ionogram(frame, freq, rng, out, RenderSpec()))
    results["first_render_s"] = round(dt, 4)
    _, dt = timed(lambda: render_raw_ionogram(frame, freq, rng, out, RenderSpec()))
    results["cached_render_path_rewrite_s"] = round(dt, 4)

    n = store.n_frames()
    ids = list(range(1, min(n, 25) + 1))
    frames = [store.get_frame(i) for i in ids]
    cout = ensure_dir(app_root() / "workspaces" / "_bench") / "contact.png"
    _, dt = timed(
        lambda: render_contact_sheet(frames, freq, rng, cout, rows=5, cols=5)
    )
    results["contact_sheet_frames"] = len(frames)
    results["contact_sheet_s"] = round(dt, 4)

    # mini batches
    for label, count in [("batch_12", 12), ("batch_144", 144)]:
        take = [1 + (i * max(1, n // max(count, 1))) % n for i in range(min(count, n))]
        t0 = time.perf_counter()
        for i in take:
            store.get_frame(i)
        results[f"{label}_frame_access_s"] = round(time.perf_counter() - t0, 4)
        results[f"{label}_count"] = len(take)

    results["cache_hits"] = store.stats["cache_hits"]
    results["cache_misses"] = store.stats["cache_misses"]
    results["hardware_note"] = "See host OS; script does not claim acceleration without these timings."

    out_json = Path(args.out) if args.out else app_root() / "docs" / "IML2_BENCHMARK_RAW.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print("Wrote", out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
