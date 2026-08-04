# PHASE 4C.1e.2b Acceptance Report

**Phase:** Stale Deferred Frame-Load Guard, Sequence Manual-Selection Integrity, and Pending Features State Closure  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.2b`  
**Mode:** shadow-only  
**Date:** 2026-08-04  

## Owner result

After Phase 4C.1e.2a:

- **490 passed**
- **2 failed**
- **9 unrelated sklearn warnings**

Prior scientific validators were green (registry, synthetic geometry, V2/morphology shadow, i18n, docs).

## Shared root-cause analysis

Both remaining failures shared one asynchronous frame-identity defect:

1. Constructor schedules `_deferred_first_activate` → `activate(force_load=True)` → `QTimer.singleShot(0, refresh)`.
2. Sequence tests establish frame **10** on the selector.
3. A later `QApplication.processEvents()` runs the deferred **`FeatureDiagnosticsPage.refresh`**.
4. `refresh` rewrote the selector from `want = int(snap.frame)` where `snap.frame` comes from `session.current_frame` (still **1** when intent was applied only via `QSpinBox.setValue` / before session intent was bumped).
5. Features empty-state then evaluated membership for frame **1** → outside-sequence text instead of pending for frame **10**.

## Exact stale callback / function found

**Function:** `FeatureDiagnosticsPage.refresh`  
**Deferred schedule path:**

1. `FeatureDiagnosticsPage.__init__` → `QTimer.singleShot(0, self._deferred_first_activate)`
2. `_deferred_first_activate` → `activate(force_load=True)`
3. `activate` → `QTimer.singleShot(0, … _run_deferred_refresh …)` (formerly bare `self.refresh`)
4. Stale `refresh` wrote `frame_spin` / `frame_slider` to `snap.frame` (1) and scheduled a frame-1 load

Secondary writers audited and guarded:

| Writer | Role after fix |
|---|---|
| `_goto_frame` | Bumps navigation generation; authoritative intent |
| `_schedule_frame_load` / `_on_frame_loaded` | Capture/validate nav gen + intended frame; load completion cannot rewrite selector |
| `_on_session_frame_changed` | Ignores stale Viewer/session frame when local intent is newer |
| `_use_viewer_frame` | Explicit accept flag for intentional Viewer sync |
| `_hydrate_sequence_row_to_inspector` | Intentional Follow/row navigation with reason + nav gen |

## Frame-navigation generation architecture

- `self._frame_navigation_generation` — monotonic int  
- `self._intended_frame` — selected/intended frame  
- `self._pending_frame_request` — `{request_generation_id, navigation_generation, frame_index, source_sha, reason, applied, discard_reason}`  
- `_bump_frame_navigation(frame, reason=…)` on every intentional navigation  
- Deferred refresh captures `scheduled_nav_gen` and discards frame rewrites when generation advanced  
- Profiler events only (`fd_frame_navigation`, `fd_frame_load_discarded`, `fd_refresh_discarded`) — not shown in normal UI  

Request reasons used: `initial_page_activation`, `source_ready`, `user_frame_entry`, `previous_next`, `viewer_sync`, `sequence_start`, `sequence_follow`, `sequence_row_selection`, `resume_follow`.

## Intended-vs-loaded frame contract

| Concept | Authority |
|---|---|
| Intended / selected frame | `_intended_frame` (+ spin/slider kept in sync) |
| Loaded / displayed data | `_loaded_frame` after compatible load apply |
| Pending Features / sequence membership UI | **intended** frame via `_authoritative_frame()` |
| Late load completion | May update `_loaded_frame` only when gen/intent/source match; **never** becomes new intent |

## Manual Follow-off behaviour

When Follow is off / manual selection active and current intended frame is 10:

`frame_done` for frame 20 may update the sequence row, progress, and last-completed metadata.

It must not change: spin, slider, `_intended_frame`, `_loaded_frame`, Features identity, Summary, candidate, Evidence/Review identity, or force-select another row’s inspector hydrate path.

## Follow-on behaviour

Valid `frame_done` with Follow on still hydrates via `_hydrate_sequence_row_to_inspector` → `_goto_frame(..., reason="sequence_follow")`, advancing navigation generation and invalidating earlier requests.

## Pending Features correction

Empty-state resolver uses `_authoritative_frame()` (intended). For intended frame 10 inside `_sequence_frames` with no result: pending/not-finished message — not outside-sequence text keyed off a stale loaded/session frame 1.

## Viewer / source callback guards

- Stale `session.events.frame_changed` ignored when local nav generation is ahead and frames differ, unless `_viewer_sync_accept` (Use Viewer Frame).
- Deferred refresh with mismatched nav gen updates source card only.
- `_on_frame_loaded` rejects stale request gen, nav gen, or frame≠intent.
- `frame_done` still rejects mismatched V2 generation / source SHA.

## Files changed

| Path |
|---|
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `tests/test_phase4c1e2_sequence_follow.py` |
| `tests/test_phase4c1e_layout_sequence_state.py` |
| `docs/PHASE4C1E2B_ACCEPTANCE_REPORT.md` *(this file)* |

## Tests changed but not run

Updated helpers/assertions for intended-frame authority; added regressions for:

- stale deferred refresh rejection  
- stale frame-load completion rejection  
- stale Viewer sync rejection  
- Follow-on selects completed frame  
- spin/slider atomic sync  
- source SHA mismatch discard on `frame_done`  
- Build Identity phase `4C.1e.2b`  

**This implementation session did not execute pytest, validators, linters, builds, packaging, or SHA commands.**

## No EXE / no SHA

- No EXE built.  
- No SHA-256 calculated.  

## Scientific non-claims

No changes to V2 calculations, geometry/candidate thresholds, cache scientific identity, evidence/review semantics, RuleEngine, or production enablement. No claim that tests or validators passed in this session.

## Owner re-verification commands

```text
pytest tests/test_phase4c1e2_sequence_follow.py -q
pytest tests/test_phase4c1e2_sequence_follow.py::test_other_frame_result_does_not_overwrite_manual_selection -q
pytest tests/test_phase4c1e2_sequence_follow.py::test_active_features_tab_pending_then_hydrated -q
pytest tests/test_phase4c1e2_sequence_follow.py::test_stale_deferred_refresh_does_not_reset_intended_frame -q
pytest -q
```

Do not begin Phase 4C.2 until owner accepts this async identity correction.
