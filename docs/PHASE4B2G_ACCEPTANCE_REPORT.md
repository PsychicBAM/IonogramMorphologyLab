# Phase 4B.2g — Real-Archive Performance Recovery, Minimal Feature Diagnostics UI, Help/Source De-cluttering

**Status:** implementation complete (runtime / UX only)  
**Date:** 2026-08-03  
**Feature version preserved:** `iml2-0.2.0`  
**Constraints honored:** Phase 4B.3 scientific geometry unchanged; RuleEngine unchanged; V2 shadow-only; Phase 4C not started; no commit/push.

## Real freeze root cause

Packaged-EXE freezes (≈40–60 s V2, ≈90–120 s navigation) were inconsistent with worker-only V2 science time (~1–2 s/frame on `Am_all_2014-10-15.mat`). Root causes on the UI path:

1. **Full MAT reopen / parse** for Feature Diagnostics independent of Viewer FrameStore/Zarr  
2. **Full source SHA-256** of ~192 MB on snapshot/refresh and store init  
3. **Eager V2 cache deserialize of all masks** on every frame (all-layers load ≈0.45 s and previously competed with or exceeded science time when repeated)  
4. **Slider/spin submitting every intermediate value**, stacking obsolete loads  
5. **Auto-attempting heavy cache work** on frame change instead of summary-only + raw display  

Synthetic-only audits hid (1)–(3) because demo MATs are tiny.

## Operations removed from slider / spinner events

| Control | Before | After |
|---------|--------|-------|
| Slider drag | Could trigger loads | Updates **labels only** |
| Slider release | — | **One** `_goto_frame` |
| Spin typing | Debounced load each change | Enter / focus-loss / longer debounce; latest value only |
| Previous / Next | Immediate | Still immediate |
| Rapid 1→…→421 | Multiple completions | Generation invalidate; only latest applied |

## Actual frame-source path used

Priority in `FrameLoadWorker`:

1. FrameStore LRU (`memory`)  
2. Zarr (`zarr`)  
3. In-process loaded MAT (`loaded_mat`)  
4. Disk fallback (counted)

Path recorded per load as `frame_source_path`. FD does **not** call `ensure_store()` / build Zarr on the UI thread; it only reuses an already-valid `session.frame_store`.

## MAT reopen count / SHA calculation count

Real-archive script (`docs/FEATURE_DIAGNOSTICS_REAL_ARCHIVE_PERFORMANCE.md`):

- Full MAT load once: **~3.0 s** (192 MB)  
- SHA once: **~0.78 s**  
- After SHA remembered: **0 recalcs** across 20 navigation peeks  
- Session `get_source_sha(allow_compute=False)` + `resolve_active_source` no longer hash on every refresh  

## UI event-loop latency

Worker-equivalent navigation after Zarr ready: **median ~0.08 s** (Zarr frame + summary).  
Cancel: UI sets «Отмена запрошена…» and invalidates generation **immediately** without waiting for the worker.

Manual packaged-EXE still required for: window move / Not responding / Cancel click-to-ack under load.

## Cache summary / heavy-layer format

`V2FeatureCache`:

- `summary_index.json` + `result.json` — lightweight  
- `masks/*.npy` — per-layer heavy arrays  
- `load_summary()` on frame select  
- `load_layer` / `load_layers` only for visible overlays  
- Frame change does **not** auto-run V2  

Measured on real archive:

| Op | Median |
|----|--------|
| Summary load | 0.041 s |
| One layer | 0.027 s |
| All layers | 0.445 s |
| Uncached V2 | 1.32 s |
| Serialize | 0.049 s |

## Uncached / cached timing (real archive)

Primary: `Am_all_2014-10-15.mat` (192 MB, 368640×400).  
Secondary: `Am_all_2013-01-01.mat` (173 MB).

See `docs/FEATURE_DIAGNOSTICS_REAL_ARCHIVE_PERFORMANCE.md` and `docs/_fd_real_perf_raw.json`.

## Cancel acknowledgement

`_cancel_run` immediately: `_running=False`, new `_v2_generation_id`, inline «Отмена запрошена…», buttons restored. Stale finished payloads ignored.

## Help drawer behavior

Large always-on explanation removed from the main stack. Compact `?` / Справка opens a drawer; first-visit expand tracked via `ux.fd_help_expanded_once`; open/pin/width persisted under `ux.fd_help_*`.

## Source-card removal

Full `ActiveSourceCard` remains on **Import**.  
Viewer / Batch / Raw Signals / MATLAB Studio / Feature Diagnostics use `CompactSourceStrip` (filename • frame • time • status + Change / Import / Technical details).  
Empty states avoid «(нет проекта): нет проекта».

## Compact layout / sequence / layers

- Page renamed: **«Диагностика следа и геометрии» / “Trace and Geometry Diagnostics”**  
- Sequence config behind «Настроить последовательность»  
- Layers behind collapsible drawer + presets  
- Secondary actions under «Дополнительно…»  
- Human status strings for normal UX; technical counters demoted  

## Full test count

| Suite | Result |
|-------|--------|
| Full `pytest tests` | **312 passed** |
| Validators | shadow OK; registry 93; synthetic geometry 17/17 `iml2-0.2.0`; i18n OK; docs OK |

## Remaining blockers (honest)

1. **Packaged-EXE UI heartbeat** under concurrent V2 on Windows must still be measured by owner (§19).  
2. If Viewer Zarr was never built, FD falls back to in-process MAT (still off UI thread) — first open of a cold source remains expensive once, not per slider tick.  
3. Building Zarr (~17 s for this archive) remains a one-time cost when Viewer cache is created.  
4. Separate-process offload for GIL-bound V2 is **not** required on this workstation for science time (~1–2 s), but remains an option if EXE still freezes after UI-path fixes.

**Do not claim packaged-EXE performance PASS without owner §19 timings.** Worker-path measurements already show navigation and summary cache are in the tens of milliseconds once Zarr + SHA are ready.

## Packaged EXE SHA-256

`60C9D1034965247DFFE809CFE466E210A396EEB5F92C3602264CF71F47795AB3`

Path: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Explicit non-claims

- No scientific validation  
- No Phase 4C classification  
- V2 remains shadow-only  
- Feature Pipeline V2 geometry unchanged  
