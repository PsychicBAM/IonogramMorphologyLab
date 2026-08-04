# Feature Diagnostics Performance Audit (Phase 4B.2f)

**Date:** 2026-08-03  
**Feature version:** `iml2-0.2.0` (unchanged)  
**Environment:** synthetic MAT lab profile (`scripts/profile_feature_diagnostics_perf.py`)  
**Note:** Packaged-EXE wall times on full-day `Am_all_*.mat` archives will be higher for first matrix load; relative first-run vs cached-run behavior matches the architecture below.

## Bottlenecks identified (pre-fix → fix)

| Bottleneck | Pre-4B.2f | Fix |
|------------|-----------|-----|
| Full MAT + SHA-256 on every frame change (UI thread) | Blocking | `FrameLoadWorker` + cached SHA/matrix by mtime/size |
| No request generation | Stale frames/masks applied | `FrameDiagnosticContext` + generation guard |
| Layer/zoom recomputed full pipeline-ish work | Rebuilt bases every toggle | `DisplayLayerCache` recomposite only |
| Progress spam | Many UI updates | 100 ms throttle (~10 Hz) |
| Sequence contact sheet eager | Risk of full overlays | Lazy / on explicit request |

## Timing breakdown (synthetic baseline)

Values from `docs/_fd_perf_raw.json` (median / p95 seconds).

| Stage | Median (s) | p95 (s) |
|-------|------------|---------|
| First frame load (hash + matrix + extract) | 0.040 | 0.040 |
| Next-frame navigation (cached matrix) | 0.0076 | 0.0081 |
| Viewer-equivalent render (jet display) | 0.013 | 0.015 |
| Cache-key generation | 0.00047 | 0.00064 |
| Cache lookup (status) | ~5e-5 | ~8e-5 |
| Uncached V2 run (+ save) | 0.108 | 0.151 |
| Cached V2 load (deserialize) | 0.567 | 0.782 |
| Overlay composition | 0.0011 | 0.0023 |
| Sequence of 13 frames (wall, with reuse) | 2.04 total | — |

**Interpretation**

- After the first matrix load, navigation is ~5× faster (SHA/matrix reuse).
- Uncached V2 dominates scientific work; repeated identical runs must hit the V2 feature cache (worker reports `cache_hits=1`, `recomputed=0`).
- Cached load time on synthetic includes mask array deserialization; still avoids recomputing the pipeline. On real archives, first MAT open dominates more than deserialize.
- Overlay toggles stay in the millisecond range when display layers are cached.

## Packaged-EXE measurement checklist (owner)

Record median/p95 on a real Am_all file for:

1. First frame load  
2. Uncached V2  
3. Cached V2  
4. Next-frame navigation (1→2→3→90→421)  
5. Sequence of 13 frames (e.g. 05:00–07:00 every 10 minutes)

Confirm UI stays interactive (progress updates, Cancel works, no stuck `saving_cache`).

## Architecture timing points

Worker stages: `loading_frame` → `checking_cache` → `loaded_from_cache` | `computing` → `saving_cache` → terminal `completed` / `cancelled` / `failed`.

UI shows separately: Viewer frame cache hint, V2 feature cache status, display-layer cache status, and compose time.
