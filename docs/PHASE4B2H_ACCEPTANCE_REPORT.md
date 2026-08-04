# Phase 4B.2h Acceptance Report

**Phase:** Packaged-EXE Performance Recovery, Persistent Pages, Process Isolation, and Balanced Diagnostics Layout  
**Feature Pipeline V2:** `iml2-0.2.0` (geometry unchanged; shadow-only)  
**Date:** 2026-08-03  
**Scientific validation:** not claimed  
**Phase 4C:** not started  
**Git:** no commit / no push

---

## 0. Prior claim override

Manual packaged-EXE QA showed freezes that contradicted Phase 4B.2g worker-path timings:

| Observation (owner EXE) | Prior worker-path claim |
|---|---|
| MAT readiness ~35 s | MAT load ~3 s |
| Diagnostics open ~40 s | n/a |
| First V2 ~15 s | uncached ~1.3 s |
| Cached V2 ~10 s | summary ~0.04 s |
| Page switch ~4 s | n/a |
| Language switch freezes | n/a |

**Packaged EXE performance status after 4B.2g = FAIL.**  
This phase targets those freeze locations. New packaged-EXE timings require owner re-test of the **new** build SHA (below). Until that re-test, **performance PASS is not claimed**.

---

## 1. Exact freeze locations (root causes addressed)

1. **Eager construction of Feature Diagnostics** at application startup (large widget tree + double refresh).
2. **`FeatureDiagnosticsPage.retranslate()` → `refresh()`** on every language change (scheduled frame load / cache work).
3. **`MainWindow._navigate_key` always called `FD.refresh()`**, reloading frames on every page visit.
4. **V2 QThread still held the GIL** during CPU-bound pipeline work → Windows “Not responding”.
5. **Cache hit path used full `cache.load()`** (all masks) inside the worker (~10 s class cost).
6. **Help drawer / large banner / stacked right column** compressed the canvas and inspector.

---

## 2. Page instance / activation counters

| Counter | Behaviour |
|---|---|
| `page_instance_created_count` | Incremented once when a lazy page is materialized |
| `page_activation_count` | Incremented on every `_navigate_key` |
| Lazy pages | `feature_diagnostics`, `raw_signals`, `atlas`, `compare`, `pipeline`, `models`, `rule_test` |
| Eager pages | Home, Import, Viewer, Batch, MATLAB, Settings, … (Batch/MATLAB remain eager for existing wiring) |

Acceptance (unit-tested): repeated Viewer ↔ Diagnostics navigation does **not** recreate the FD instance.

---

## 3. MAT / Zarr / cache scan counts

| Path | Behaviour |
|---|---|
| Source service | One `SourceService` per `AppSession`; pages reuse `session.frame_store` |
| FD activation | Reuses in-memory frame when MAT path + frame unchanged |
| V2 cache | `source_index.json` for direct frame lookup; no recursive directory scan on open/nav/language |
| SHA | Still computed once and reused; not on language switch |

---

## 4. Language-switch I/O

- `set_language` sets `_retranslate_only` and skips import-list / viewer-meta / dashboard data refresh.
- FD exposes `retranslate_ui()` — **labels only**; no `refresh()`, no MAT/Zarr/cache I/O.
- Unit test: `retranslate_ui` does not call `refresh`; frame/image pointer preserved.

---

## 5. Worker process architecture

- Child entry: `IonogramMorphologyLab.exe --iml-v2-worker` (or `python -m … --iml-v2-worker`).
- Transport: temporary `.npy` frame (bounded); never the full MAT.
- UI-side `V2ProcessJobThread` checks **summary-only** cache hits in the UI process; compute runs in the child.
- Cancel: invalidates generation immediately; terminates child process if needed; stale results discarded.
- Fallback: if the child fails to start, in-process pipeline runs (still generation-guarded).
- Process crash must not close the UI process (QProcess isolation).

---

## 6. Cache summary / heavy layers

- `load_summary` / `summary_index.json` / `source_index.json`
- Heavy masks loaded only for visible layers via `load_layers(names)`
- Cached Run V2 no longer deserializes all masks up front

---

## 7. UI changes

- Help drawer opens from the **right**; compact `?` control; pin/open remembered.
- Duplicate large page banner removed from FD (MainWindow title + small shadow badge).
- Right inspector uses tabs: Summary / Features / Future 4C / Geometry review / Technical details.
- Features tab populates lazily.
- Technical Details includes copyable **Build Identity** (EXE path, SHA-256, versions, cache/workspace roots).
- Opt-in profiler: `IML_PACKAGED_PERF=1` or Settings → `performance.packaged_exe_profiler` → `workspaces/_packaged_exe_perf/<stamp>/`.

---

## 8. Automated tests / validators

| Check | Result |
|---|---|
| Full `pytest tests/` | **329 passed** |
| `validate_feature_shadow_mode` | OK |
| `validate_feature_registry_v2` | OK registry=93 |
| `validate_synthetic_geometry_v2` | OK 17/17 `iml2-0.2.0` |
| `validate_i18n` | OK |
| `validate_docs` | OK |

---

## 9. Packaged EXE

| Field | Value |
|---|---|
| Previous SHA (4B.2g) | `60C9D1034965247DFFE809CFE466E210A396EEB5F92C3602264CF71F47795AB3` |
| New SHA (4B.2h) | `E48C69CEECAFE0EEE16B1C4A84AADF58D2ED3F3DBE9193562213DE9BD92F1B78` |
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |

---

## 10. Manual packaged-EXE QA (owner) — required for PASS

Use **only** the new SHA. Record wall times for:

1. Startup  
2. Project open  
3. Diagnostics first appearance (must show page before cold prep)  
4. Cold source readiness  
5. Warm page switch (target &lt; 0.3 s)  
6. Language switch (target &lt; 0.5 s; no freeze)  
7. Frame navigation from Zarr  
8. First V2 / repeated cached V2  
9. Cancel acknowledgement (target &lt; 0.1 s)  
10. Page switch during V2  
11. Windows “Not responding” occurrences  

Archive: `Am_all_2014-10-15.mat`  
Resolutions: 1280×720, 1366×768, 1600×900, 1920×1080 at 100/125/150%.

---

## 11. Remaining blockers

- **Performance PASS blocked** until owner completes §10 on the new EXE.
- Cold MAT inventory/classify may still cost seconds the first time a source is prepared — UI must remain interactive; report any remaining “Not responding”.
- Process worker warm-start cost is paid once per session; first V2 after cold start may include child spawn time.

---

## 12. Non-goals confirmed

- Feature Pipeline V2 scientific geometry not modified.
- Production RuleEngine not wired to V2.
- Phase 4C not started.
- No scientific validation claim.
- No git commit / push.
