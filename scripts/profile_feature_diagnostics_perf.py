"""Profile Feature Diagnostics timings for Phase 4B.2f audit (synthetic mats)."""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.fd_display import jet_like_rgb, prepare_overlay_mask
from ionogram_morphology_lab.ui.fd_frame_loader import (
    cached_amplitude_matrix,
    cached_source_sha,
    clear_fd_matrix_caches,
    frame_sha256,
)
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent


def _median_p95(samples: list[float]) -> dict:
    if not samples:
        return {"median_s": None, "p95_s": None, "n": 0}
    s = sorted(samples)
    return {
        "median_s": statistics.median(s),
        "p95_s": s[max(0, int(round(0.95 * (len(s) - 1))))],
        "n": len(s),
        "mean_s": statistics.mean(s),
    }


def main() -> None:
    td = Path(tempfile.mkdtemp(prefix="iml_fd_perf_"))
    syn = td / "syn"
    write_synthetic_mat_library(syn)
    mat = sorted(syn.glob("*.mat"))[0]
    settings = SettingsStore(td / "settings.json")
    settings.set("performance", "cache_location", str(td / "cache"))
    settings.save()
    project = create_project("perf", language="en", workspace_parent=td / "ws")
    profile = {
        "amplitude_variable_name": "Amp_all",
        "height_bins": 256,
        "frequency_bins": 400,
        "time_mapping": "matlab_index_minus_1",
    }
    cache = V2FeatureCache(settings.cache_dir())

    clear_fd_matrix_caches()
    first_load = []
    next_nav = []
    for i, frame in enumerate([1, 2, 3, 1, 2]):
        t0 = time.perf_counter()
        sha = cached_source_sha(mat)
        loaded = cached_amplitude_matrix(mat, "Amp_all")
        arr, _ = extract_frame_consistent(loaded.data, frame, height_bins=256, frequency_bins=400)
        _ = frame_sha256(arr)
        dt = time.perf_counter() - t0
        (first_load if i == 0 else next_nav).append(dt)

    raw = extract_frame_consistent(
        cached_amplitude_matrix(mat, "Amp_all").data, 1, height_bins=256, frequency_bins=400
    )[0]
    render_t = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = jet_like_rgb(raw)
        render_t.append(time.perf_counter() - t0)

    key_t = []
    for _ in range(20):
        t0 = time.perf_counter()
        key = make_cache_key(
            source_mat_sha256=cached_source_sha(mat),
            frame_index=1,
            profile_id="kfu",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        key_t.append(time.perf_counter() - t0)

    lookup_t = []
    for _ in range(10):
        t0 = time.perf_counter()
        cache.status_for(key)
        lookup_t.append(time.perf_counter() - t0)

    # Uncached V2
    cache.clear_for_source(cached_source_sha(mat))
    uncached = []
    last_hit = None
    for frame in (1, 2, 3):
        k = make_cache_key(
            source_mat_sha256=cached_source_sha(mat),
            frame_index=frame,
            profile_id="kfu",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        frame_arr, _ = extract_frame_consistent(
            cached_amplitude_matrix(mat, "Amp_all").data, frame, height_bins=256, frequency_bins=400
        )
        t0 = time.perf_counter()
        res = run_feature_pipeline_v2(
            frame_arr,
            signal_contract_id="kfu_amp_all_v1",
            profile_id="kfu",
            frame_index=frame,
            source_mat_sha256=cached_source_sha(mat),
        )
        cache.save(k, res)
        uncached.append(time.perf_counter() - t0)

    # Cached V2 load
    cached_load = []
    for frame in (1, 2, 3):
        k = make_cache_key(
            source_mat_sha256=cached_source_sha(mat),
            frame_index=frame,
            profile_id="kfu",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        t0 = time.perf_counter()
        hit = cache.load(k)
        assert hit is not None
        last_hit = hit
        cached_load.append(time.perf_counter() - t0)

    overlay_t = []
    for _ in range(5):
        t0 = time.perf_counter()
        for name, m in (last_hit["masks"] or {}).items():
            _ = prepare_overlay_mask(m)
        overlay_t.append(time.perf_counter() - t0)

    seq13_uncached = []
    # 13-frame sequence may exceed synthetic length — repeat available frames
    frames = [((i % 3) + 1) for i in range(13)]
    cache.clear_for_source(cached_source_sha(mat))
    t0 = time.perf_counter()
    for frame in frames:
        frame_arr, _ = extract_frame_consistent(
            cached_amplitude_matrix(mat, "Amp_all").data, frame, height_bins=256, frequency_bins=400
        )
        k = make_cache_key(
            source_mat_sha256=cached_source_sha(mat),
            frame_index=frame,
            profile_id="kfu",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        if cache.load(k) is None:
            res = run_feature_pipeline_v2(
                frame_arr,
                signal_contract_id="kfu_amp_all_v1",
                profile_id="kfu",
                frame_index=frame,
                source_mat_sha256=cached_source_sha(mat),
            )
            cache.save(k, res)
    seq13_uncached.append(time.perf_counter() - t0)

    report = {
        "environment": "synthetic_mat_lab_profile",
        "mat": str(mat.name),
        "note": "Packaged-EXE wall times on real Am_all archives will differ; these are reproducible CI/dev baselines.",
        "first_frame_load": _median_p95(first_load),
        "next_frame_navigation": _median_p95(next_nav),
        "viewer_equivalent_render": _median_p95(render_t),
        "cache_key_generation": _median_p95(key_t),
        "cache_lookup": _median_p95(lookup_t),
        "uncached_v2_run": _median_p95(uncached),
        "cached_v2_load": _median_p95(cached_load),
        "overlay_composition": _median_p95(overlay_t),
        "sequence_13_frames_wall_s": seq13_uncached[0],
        "project": str(project.root),
    }
    out = Path(__file__).resolve().parents[1] / "docs" / "_fd_perf_raw.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
