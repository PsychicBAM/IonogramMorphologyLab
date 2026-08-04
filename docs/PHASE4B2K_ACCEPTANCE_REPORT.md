# Phase 4B.2k Acceptance Report

**Phase:** Eliminate Repeated Source-MAT Opens from UI Paths and Make Active-Source Metadata Truly In-Memory  
**Feature Pipeline V2:** `iml2-0.2.0` (geometry unchanged; shadow-only)  
**Date:** 2026-08-03  
**Owner profiler source of truth:** session `20260803T185943Z` (EXE SHA `AE704339…`)  
**Scientific validation:** not claimed  
**Phase 4C:** not started  
**Git:** no commit / no push

---

## 0. Owner profiler facts (pre-fix)

| Metric | Observed |
|---|---|
| Production cache root | `%LOCALAPPDATA%/IonogramMorphologyLab/cache` (OK) |
| FD page creation | ~0.046 s (OK) |
| V2 worker compute | ~0.8–1.1 s (OK) |
| Cancel closes app | no (OK) |
| `file_io` records | 1610 |
| **source_mat opens** | **749** |
| **source_mat stats** | **358** |
| source_mat ops total | 1107 |
| Warm page activation | ~6 opens + 3 stats |
| FD activation | ~12 opens + 6 stats |
| Language switch | ~6 opens + 3 stats; `lang.source_strips_visible` ~1.3 s |
| Uncached V2 pre_submit | ~4.9–7.9 s |
| Cached post / apply | still opens MAT |
| Heartbeat max | **12.313 s** |

**Conclusion:** Persistent V2 worker is not the bottleneck. Repeated `resolve_active_source` → `classify_mat_source` → `inventory_mat` (whosmat/h5py + hash paths) on every strip refresh drove the opens.

---

## 1. Exact functions responsible for 749 MAT opens

Primary chain (warm UI):

1. `MainWindow._refresh_source_cards(light=True)` — called from navigation and (previously) language switch  
2. `resolve_active_source(session)` — rebuilt snapshot every call  
3. `classify_mat_source(..., try_frame=False)` — once per inventory path + active path  
4. `inventory_mat()` → SciPy `whosmat` / h5py variable scan (+ related opens)

Secondary chains:

5. `FeatureDiagnosticsPage.activate` / `refresh` / `_check_prerequisites` / `_cache_key` / `run_shadow` / `_populate_summary_from_ser` / `_on_worker_finished` → each called `resolve_active_source` again  
6. `refresh` / `_check_prerequisites` additionally called `classify_mat_source` and `Path.is_file()` / `.resolve()` (stats)

---

## 2. Source snapshot architecture

| Piece | Behaviour |
|---|---|
| Type | Expanded `ActiveSourceSnapshot` (path, size, mtime, SHA, variable, shape, dtype, frame count, profile/contract, readiness, Viewer/Zarr/V2 cache roots, warnings, validation identity) |
| Storage | `AppSession._active_source_snap` + `_source_classifications` cache |
| Build | `rebuild_active_source_snapshot()` — import / `set_active_mat` / explicit Refresh Source / profile change |
| Warm read | `resolve_active_source(..., force_rebuild=False)` — returns cached snap; updates only frame/time in memory |
| Path compare | `paths_equal()` — no `resolve()` / `stat()` |
| Language | `_retranslate_source_strips_only()` — `card.retranslate()` on cached strip data; **zero** resolve |

---

## 3. Source-service lifetime

- One `SourceService` per `AppSession` (`__post_init__`).  
- One `FrameStore` via `session.ensure_store()`; pages must use `get_existing_store()` for warm paths.  
- Counters: `source_service_instances`, `adapter_creation_count`, `MAT_logical_open_count`, `variable_inventory_scan_count`, `frame_store_instances`.  
- Inventory scans counted when classifications are (re)computed.

---

## 4. Open/stat counts — before vs after (code intent)

| Scenario | Before (owner) | After (code contract) |
|---|---|---|
| Viewer → Diagnostics → Settings → Diagnostics | ~6–12 opens / nav | **0** source_mat open/stat |
| RU → EN → RU | ~6 opens / switch | **0** |
| V2 pre context validation (active unchanged) | ~2 s + many opens | **0** MAT I/O; snapshot + context |
| Cache validity | reopened MAT | snapshot SHA / identity only |
| Post-result | resolve again | cached snapshot only |
| Explicit Refresh Source | — | rebuild allowed (intentional) |

Owner must confirm warm `source_mat` open/stat = 0 on the new EXE.

---

## 5. Profiler byte-semantics correction

| Field | Meaning |
|---|---|
| `file_size` | size observed at open (seek end) |
| `bytes_read` / `actual_bytes_read` | **0** on mere `open()` |
| `bytes_unknown` | true for open without measured read |
| `open_count` / `read_call_count` | separate counters |

Opening a ~192 MB MAT must no longer be reported as a 192 MB read.

---

## 6. Automated verification

| Check | Result |
|---|---|
| Full `pytest` | **371 passed** |
| New tests | `tests/test_phase4b2k_source_snapshot.py` |
| Strip / lang / nav zero MAT | Covered |
| Context validation / cache key / post-result | Covered |
| Profiler file_size vs bytes_read | Covered |
| Cancel / RuleEngine / V2 shadow | Covered |

---

## 7. Packaged EXE

| Field | Value |
|---|---|
| Previous (4B.2j owner-tested) | `AE704339688CF543F508EF0449B712C8EE4F7C810A2494D830AC8BB8573985FD` |
| **New (4B.2k)** | `DE2522F986C8A41A482BD4512A44D207F3C80C03FA70BFE4D76504D6447E6C79` |
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |

Enable: `IML_PACKAGED_PERF=1`  
MAT: `Am_all_2014-10-15.mat`  
Separate cold source preparation from the warm segment. Validate with `scripts/validate_packaged_perf_trace.py`.

---

## 8. Owner warm scenario (required)

After source ready + fresh profiler segment:

1. Viewer → Diagnostics → Settings → Diagnostics  
2. RU → EN → RU  
3. Uncached V2 on current displayed frame  
4. V2 on second frame  
5. Cached V2 on first frame  
6. Switch pages during V2; Cancel; close  

Required evidence:

- warm `source_mat` open = 0, stat = 0  
- no MAT under `nav.source_strip_light`, `language_switch`, `v2.pre.context_validation`, `v2.pre.cache_validity_check`, `v2.post_result`  
- cache hit → no worker request  
- heartbeat p95 &lt; 0.35 s; warm nav/lang max &lt; 1 s  

**Performance PASS is not claimed** until that session is validated.

---

## 9. Remaining blockers

1. Owner packaged warm-segment re-test not yet run.  
2. Cold import / first activation still opens MAT (by design).  
3. Explicit Refresh Source still rebuilds (by design).  
4. Non-process `V2DiagnosticsWorker` / Raw Signals full refresh paths may still open MAT when used — outside the warm strip/nav/lang/V2-process contract.  
5. Compose/render may still cost UI time independently of MAT opens.

---

## 10. Non-goals confirmed

- V2 scientific geometry unchanged  
- Persistent `subprocess.Popen` worker retained  
- Cancel state machine retained  
- Production cache-root correction retained  
- RuleEngine not wired to V2; V2 shadow-only  
- Phase 4C not started  
- No scientific validation claim  
- No git commit / push  
