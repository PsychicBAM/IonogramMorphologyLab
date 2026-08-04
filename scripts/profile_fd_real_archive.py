"""Profile Feature Feature Diagnostics paths on real Am_all archives (Phase 4B.2g)."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ARCHIVE = Path(r"E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat")
ARCHIVE2 = Path(r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat")
OUT = ROOT / "docs" / "FEATURE_DIAGNOSTICS_REAL_ARCHIVE_PERFORMANCE.md"
RAW = ROOT / "docs" / "_fd_real_perf_raw.json"


def _write_report(text: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")


def _med(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def profile_archive(path: Path) -> dict:
    import numpy as np
    import tempfile

    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.cache.frame_store import FrameStore
    from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
    from ionogram_morphology_lab.ui.fd_frame_loader import (
        cached_source_sha,
        clear_fd_matrix_caches,
        nav_stats,
        peek_cached_source_sha,
        reset_nav_stats,
    )
    from ionogram_morphology_lab.utils.hashing import sha256_file

    clear_fd_matrix_caches()
    reset_nav_stats()
    report: dict = {"archive": str(path), "size_bytes": path.stat().st_size}

    t0 = time.perf_counter()
    sha = sha256_file(path)
    report["source_sha_s"] = time.perf_counter() - t0
    report["source_sha"] = sha[:16]

    t0 = time.perf_counter()
    loaded = load_amplitude_matrix(path, variable="Amp_all")
    report["mat_load_s"] = time.perf_counter() - t0
    report["shape"] = list(loaded.data.shape)

    td = Path(tempfile.mkdtemp(prefix="iml_fd_real_"))
    settings = SettingsStore(td / "settings.json")
    settings.set("performance", "cache_location", str(td / "cache"))
    settings.save()
    profile = {
        "profile_id": "kfu_cyclone_2013_2014",
        "amplitude_variable_name": "Amp_all",
        "height_bins": 256,
        "frequency_bins": 400,
        "frames_per_file": 1440,
        "matrix_layout": "frames_stacked_rows",
        "profile_verification_status": "provisional",
    }

    t0 = time.perf_counter()
    store = FrameStore(path, profile, cache_root=td / "cache", source_sha256=sha)
    report["framestore_init_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    st = store.build_cache()
    report["zarr_build_s"] = time.perf_counter() - t0
    report["zarr_valid"] = bool(st.valid)

    frames = [1, 90, 421, 720, 1301, 1440]
    extract_mat = []
    extract_zarr = []
    for fi in frames:
        t0 = time.perf_counter()
        raw, _ = extract_frame_consistent(loaded.data, fi, height_bins=256, frequency_bins=400)
        extract_mat.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        _ = store.get_frame(fi, prefetch=False)
        extract_zarr.append(time.perf_counter() - t0)

    report["extract_from_loaded_mat_median_s"] = _med(extract_mat)
    report["extract_from_zarr_median_s"] = _med(extract_zarr)
    report["extract_from_zarr_p95_s"] = sorted(extract_zarr)[max(0, int(0.95 * (len(extract_zarr) - 1)))]

    # SHA peek during navigation must not recompute
    reset_nav_stats()
    for _ in range(20):
        peek_cached_source_sha(path)
        cached_source_sha(path, allow_compute=False)
    report["nav_sha_calcs_after_20_peeks"] = nav_stats()["sha_calcs"]

    v2_cache = V2FeatureCache(td / "cache")
    uncached = []
    summary_load = []
    one_layer = []
    all_layers = []
    serialize = []
    for fi in (1, 421, 720):
        raw = store.get_frame(fi, prefetch=False)
        key = make_cache_key(
            source_mat_sha256=sha,
            frame_index=fi,
            profile_id="kfu_cyclone_2013_2014",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        t0 = time.perf_counter()
        res = run_feature_pipeline_v2(
            np.asarray(raw),
            signal_contract_id="kfu_amp_all_v1",
            profile_id="kfu_cyclone_2013_2014",
            frame_index=fi,
            source_mat_sha256=sha,
        )
        uncached.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        v2_cache.save(key, res)
        serialize.append(time.perf_counter() - t0)

    for fi in (1, 421, 720):
        key = make_cache_key(
            source_mat_sha256=sha,
            frame_index=fi,
            profile_id="kfu_cyclone_2013_2014",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        t0 = time.perf_counter()
        hit = v2_cache.load_summary(key)
        summary_load.append(time.perf_counter() - t0)
        assert hit is not None
        t0 = time.perf_counter()
        _ = v2_cache.load_layer(key, "trace_accepted")
        one_layer.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        _ = v2_cache.load_layers(key)
        all_layers.append(time.perf_counter() - t0)

    report["uncached_v2_median_s"] = _med(uncached)
    report["uncached_v2_max_s"] = max(uncached)
    report["cache_serialize_median_s"] = _med(serialize)
    report["summary_load_median_s"] = _med(summary_load)
    report["one_layer_load_median_s"] = _med(one_layer)
    report["all_layers_load_median_s"] = _med(all_layers)

    # Approximate UI path: zarr frame + summary only (no V2)
    ui_nav = []
    for fi in frames:
        t0 = time.perf_counter()
        _ = store.get_frame(fi, prefetch=True)
        key = make_cache_key(
            source_mat_sha256=sha,
            frame_index=fi,
            profile_id="kfu_cyclone_2013_2014",
            signal_contract_id="kfu_amp_all_v1",
            profile=profile,
        )
        _ = v2_cache.load_summary(key)  # may miss for some frames
        ui_nav.append(time.perf_counter() - t0)
    report["frame_nav_zarr_plus_summary_median_s"] = _med(ui_nav)
    report["frame_nav_zarr_plus_summary_max_s"] = max(ui_nav)
    report["notes"] = (
        "Script measures worker-equivalent paths on the real archive. "
        "Packaged-EXE UI event-loop latency still requires manual owner measurement."
    )
    return report


def main() -> int:
    if not ARCHIVE.is_file():
        _write_report(
            "# Feature Diagnostics Real Archive Performance\n\n"
            f"Real archive was not present at `{ARCHIVE}`.\n\n"
            "Profiling was skipped gracefully.\n"
        )
        return 0

    reports = [profile_archive(ARCHIVE)]
    if ARCHIVE2.is_file():
        try:
            reports.append(profile_archive(ARCHIVE2))
        except Exception as exc:  # noqa: BLE001
            reports.append({"archive": str(ARCHIVE2), "error": str(exc)})

    RAW.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    r0 = reports[0]
    lines = [
        "# Feature Diagnostics Real Archive Performance (Phase 4B.2g)",
        "",
        f"**Primary archive:** `{r0['archive']}`",
        f"**Size:** `{r0['size_bytes']}` bytes (~{r0['size_bytes']/1e6:.1f} MB)",
        f"**Shape:** `{r0.get('shape')}`",
        "",
        "## Measured wall times (Python worker path)",
        "",
        "| Operation | Seconds |",
        "|-----------|--------:|",
        f"| Source SHA-256 (once) | {r0.get('source_sha_s'):.3f} |",
        f"| Full MAT load | {r0.get('mat_load_s'):.3f} |",
        f"| FrameStore init (SHA supplied) | {r0.get('framestore_init_s'):.3f} |",
        f"| Zarr cache build | {r0.get('zarr_build_s'):.3f} |",
        f"| Frame extract from loaded MAT (median) | {r0.get('extract_from_loaded_mat_median_s'):.4f} |",
        f"| Frame extract from Zarr (median) | {r0.get('extract_from_zarr_median_s'):.4f} |",
        f"| Frame extract from Zarr (p95) | {r0.get('extract_from_zarr_p95_s'):.4f} |",
        f"| Uncached V2 compute (median) | {r0.get('uncached_v2_median_s'):.3f} |",
        f"| Uncached V2 compute (max) | {r0.get('uncached_v2_max_s'):.3f} |",
        f"| V2 cache serialize (median) | {r0.get('cache_serialize_median_s'):.3f} |",
        f"| V2 summary load (median) | {r0.get('summary_load_median_s'):.4f} |",
        f"| One heavy layer load (median) | {r0.get('one_layer_load_median_s'):.4f} |",
        f"| All heavy layers load (median) | {r0.get('all_layers_load_median_s'):.3f} |",
        f"| Nav: Zarr frame + summary (median) | {r0.get('frame_nav_zarr_plus_summary_median_s'):.4f} |",
        f"| Nav: Zarr frame + summary (max) | {r0.get('frame_nav_zarr_plus_summary_max_s'):.4f} |",
        f"| SHA recalcs after 20 navigation peeks | {r0.get('nav_sha_calcs_after_20_peeks')} |",
        "",
        "## Interpretation vs packaged-EXE freezes",
        "",
        "- Full MAT load (~seconds) and full SHA (~seconds) must **not** run on every slider tick.",
        "- After Zarr is ready, frame navigation is milliseconds; UI freezes of 90–120 s indicate MAT reopen/hash on the UI thread.",
        "- Loading **all** V2 masks can exceed a single V2 compute; frame change must use **summary-only** load.",
        "- Uncached V2 science time on this workstation is ~1–2 s/frame in-process; 40–60 s EXE freezes imply UI-thread MAT I/O, full-cache deserialize, or GIL-blocking work in callbacks — addressed by FrameStore-first load, SHA reuse, lazy cache, and release-only slider submit.",
        "",
        "## Manual packaged-EXE still required",
        "",
        "Record separately: slider drag responsiveness, Cancel click-to-ack, page switch during V2, Windows “Not responding”.",
        "",
        f"Raw JSON: `{RAW.name}`",
        "",
    ]
    if len(reports) > 1 and "error" not in reports[1]:
        r1 = reports[1]
        lines += [
            "## Secondary archive",
            "",
            f"`{r1['archive']}` — MAT load `{r1.get('mat_load_s'):.3f}s`, uncached V2 median `{r1.get('uncached_v2_median_s'):.3f}s`",
            "",
        ]
    _write_report("\n".join(lines))
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
