# Phase 4B.2j Acceptance Report

**Phase:** Profiler-Grounded UI-Thread Hotspot Removal, Production Cache-Root Repair, and Fast Retranslation  
**Feature Pipeline V2:** `iml2-0.2.0` (geometry unchanged; shadow-only)  
**Date:** 2026-08-03  
**Owner profiler source of truth:** session `20260803T150816Z` (EXE SHA `3153F1E2…`)  
**Scientific validation:** not claimed  
**Phase 4C:** not started  
**Git:** no commit / no push

---

## 0. Owner profiler facts that drove this phase (pre-fix)

| Metric | Observed |
|---|---|
| UI heartbeat max | **20.711 s** |
| Heartbeat ≥3 / ≥5 / ≥10 / ≥15 s | 27 / 18 / 7 / 4 |
| Language switch | 20.695 s / 19.739 s |
| FD first page creation | 5.900 s |
| FD first page activation | 8.993 s (`fd_activate` only 1.608 s) |
| Viewer activation | ~1.44–1.65 s |
| V2 cold worker | 0.913 s |
| V2 job compute | ~0.768–1.125 s |
| `file_io.jsonl` | **0 records** (tracer ineffective) |

**Conclusion from owner trace:** V2 science is not the main bottleneck. UI-thread preparation, navigation, translation, and cache-root contamination dominate. Persistent `subprocess.Popen` worker retained.

---

## 1. Pytest cache-root contamination — root cause

**Cause:** `config/user_settings.json` had been persisted with

`performance.cache_location = C:\Users\…\AppData\Local\Temp\pytest-of-abdal\pytest-158\test_cache_cleanup_never_delet0\cache`

PyInstaller bundles `config/` into the packaged EXE (`--add-data "config;config"`). Frozen startup loaded that leaked pytest fixture path as the production cache root.

**Correction:**

| Item | Value |
|---|---|
| Module | `app/cache_root.py` |
| Production cache | `%LOCALAPPDATA%\IonogramMorphologyLab\cache` |
| Production settings (frozen) | `%LOCALAPPDATA%\IonogramMorphologyLab\user_settings.json` |
| Reject markers (frozen) | `pytest-of-`, `pytest-`, `test_cache_`, pytest temp roots |
| On reject | Do not use path; fall back to production; technical warning; **no silent migration** of test artifacts |
| Repo settings | `cache_location` cleared to `""` |
| Build Identity | `resolved_cache_root`, `cache_resolution_source`, `rejected_cache_path`, `production_mode` |

Test runs under pytest still use isolated tmp caches via `resolve_cache_root(..., force_frozen=False)`.

---

## 2. Language switch

| Design | Behaviour |
|---|---|
| Immediate | Menus, navigation, status bar, **visible page only** |
| Hidden pages | `_page_language_dirty = true`; no widget-tree walk |
| Unopened lazy pages | Untouched; created later in current language |
| Forbidden on language switch | Global theme apply, icon regeneration, Help rebuild, hidden-page retranslate |

Nested spans under `language_switch` (chrome / visible page / mark dirty / deferred settings save).

| | Before (owner `20260803T150816Z`) | After (code) |
|---|---|---|
| Language switch | ~20 s UI stall | Visible-only + dirty flags (owner re-measure required) |
| Theme / icons | Could run with retranslate | **Not** called from `set_language` |

---

## 3. Feature Diagnostics page creation / activation

**Skeleton at construction:** title/badge, compact source strip, frame toolbar, quick layers, canvas placeholder, Summary tab, inspector tab shells, status line.  
**Deferred until open/use:** expert layer checkboxes, Help body text, sequence field rebuild, Features list/explain, Geometry review form, Technical details body.

| | Before | After (code target) |
|---|---|---|
| Page creation | 5.900 s | Skeleton + deferred heavy tabs (owner re-measure) |
| Activation outer | 8.993 s | Nested `nav.*` + `fd_activate` (owner re-measure) |
| Unaccounted gap | ~7 s outside `fd_activate` | Navigation spans added in MainWindow |

---

## 4. Navigation

Normal `_navigate_key` must not: global retranslate, full theme, rebuild nav, hash EXE, scan caches, reopen Zarr, `adjustSize` on large trees.  
Lazy language applied only when a dirty page is activated. Nested `nav.*` spans required for ≥95% accounting of long `page_activation` parents (validator).

---

## 5. Pre-V2 / worker / post-V2 UI

| Stage | Nested spans / behaviour |
|---|---|
| Pre-submit | `v2.pre_submit` → context validation, raw retrieval, frame copy, cache validity, progress setup, worker start |
| Worker | Unchanged persistent Popen; metrics: reuse count, bytes sent/received, compute span |
| Cache | `diagnose_lookup` records key, root, SHA, feature version, parameter hash, index/summary found, miss/invalidation reason; bare directory ≠ hit |
| Cache hit | No worker request; summary only; quick layers on demand |
| Post-result | `v2.post_result` → UI ack, apply, summary, canvas; Features/Tech only if those tabs open |

---

## 6. File-I/O profiler health

| Field | Behaviour |
|---|---|
| Hooks | `builtins.open`, `os.stat`, `os.scandir` |
| Outputs | `file_io.jsonl` with op, path, bytes, tid, duration, category |
| Health | `file_io_tracer_active`, `intercepted_operation_count`, `uninstrumented_backend_warning` |
| FAIL rule | Tracer active + 0 records during file-reading scenario |
| Deadlock fix | `stop_profiler` releases lock before `close()` / summary write |

**Note:** NumPy/Zarr native I/O may still bypass Python `open`; warning recorded. Owner session must show **non-empty** `file_io.jsonl`.

---

## 7. Validator

`scripts/validate_packaged_perf_trace.py` fails when:

- Frozen cache root is a pytest/test fixture path  
- Parent spans (`language_switch`, `page_activation`, `v2.pre_submit`, `v2.post_result`) ≥0.5 s are &lt;90% explained by children  
- Language / page activation lack nested breakdown  
- V2 pre/post breakdown missing when V2 events present  
- `file_io.jsonl` empty while tracer active in a reading scenario  
- Heartbeat max &gt; 2.0 s  

---

## 8. Automated verification

| Check | Result |
|---|---|
| Full `pytest` | **357 passed** |
| New tests | `tests/test_phase4b2j_cache_and_retranslate.py` |
| Frozen rejects pytest cache | Covered |
| Visible-only language + dirty | Covered |
| FD skeleton / lazy tabs | Covered |
| Profiler file I/O + nested spans | Covered |
| Navigation no theme / no global retranslate | Covered |
| Cancel / RuleEngine / V2 shadow | Covered (prior + smoke) |

---

## 9. Packaged EXE

| Field | Value |
|---|---|
| Previous (owner-tested 4B.2i) | `3153F1E2865D2790DD271ACAD902A7113B09B3FD60A9308017C0180C877FD071` |
| **New (4B.2j)** | `AE704339688CF543F508EF0449B712C8EE4F7C810A2494D830AC8BB8573985FD` |
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |

Enable: `IML_PACKAGED_PERF=1`  
MAT: `Am_all_2014-10-15.mat`  
Then run: start → open project → Diagnostics → Viewer↔Diagnostics → Settings → RU→EN→RU → V2 frame1 → V2 frame2 → cached frame → switch during V2 → Cancel → close.  
Validate with: `python scripts/validate_packaged_perf_trace.py workspaces/_packaged_exe_perf/<stamp>`

---

## 10. Heartbeat / performance acceptance (owner must confirm)

| Gate | Target |
|---|---|
| Heartbeat p95 | &lt; 0.35 s |
| Max during nav/language | &lt; 1.0 s |
| Cold page prep max gap | &lt; 2.0 s |
| Windows “Not Responding” | none |
| Unexplained span ≥100 ms | none |

**Performance PASS is not claimed** until a new packaged session on SHA `AE704339…` is validated.

---

## 11. Remaining blockers

1. Owner packaged-EXE QA on **new** SHA not yet run → heartbeat / language / activation timings in this report are pre-fix vs code intent only.  
2. Full NumPy/Zarr native I/O still may under-count in `file_io.jsonl` (documented warning).  
3. Compose/render still largely on UI thread (nested spans added; further offload if next trace shows ≥100 ms).  
4. Sequence form widgets still exist (hidden) at construction — further deferral possible if create-time still &gt;0.2 s.

---

## 12. Non-goals confirmed

- V2 scientific geometry unchanged  
- RuleEngine not wired to V2  
- V2 remains shadow-only  
- Persistent Popen worker retained (not rewritten)  
- Phase 4C not started  
- No scientific validation claim  
- No git commit / push  
