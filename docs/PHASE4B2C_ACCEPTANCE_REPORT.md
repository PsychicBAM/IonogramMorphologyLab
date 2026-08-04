# Phase 4B.2c — Feature Diagnostics Runtime Wiring & Active MAT Source Lifecycle

**Status:** implementation complete (runtime integration only)  
**Date:** 2026-08-03  
**Scope constraint:** No Feature Pipeline V2 geometry/threshold changes; V2 remains shadow-only; production RuleEngine unchanged; Phase 4C not started.

## Root cause

Feature Diagnostics previously gated on a nonexistent `AnalysisProject.source_mat_path` field. The real active MAT lives on `AppSession.active_mat` (set by Import via inventory). That check always failed after a normal import, producing the English-only message “Open a project with a source MAT first.” even when a MAT was imported.

## Single active-source state

Authority: `AppSession` (`active_mat`, `selected_mats`, `current_frame`, `profile*`, `frame_store`, `v2_job_status`) plus `SessionEvents` for live refresh.

Shared resolver: `ui/active_source.py` → `resolve_active_source(session)` / `ActiveSourceSnapshot`.

Consumed by: Import, Viewer, Batch Analysis, Raw Numeric Signals, Feature Diagnostics, MATLAB Studio (via `ActiveSourceCard`).

Persisted on project: `AnalysisProject.active_source_path` (+ existing `source_paths`).

## Distinctions

| State | Meaning |
|-------|---------|
| Inventory | Path in `selected_mats` / `project.source_paths` |
| Active | `session.active_mat` |
| Ready / missing / not loaded | Snapshot `SourceStatus` |

Import with `make_active=True` (default) selects the file as active and shows RU/EN confirmation.

## Source management actions

On every source card: Choose Another MAT, Set as Active, Detach Current MAT, Open Import Page, Refresh Source, Open File Folder, Remove Entry from Project.

- **Detach:** session context only; never deletes the physical MAT.
- **Remove Entry:** inventory/`source_paths` only after confirmation; never deletes the physical MAT.
- **Safe switch:** blocks active V2 / MATLAB / batch jobs; can stop Viewer playback after confirm; clears frame, diagnostic masks/results, MATLAB comparison candidates; past saved results remain keyed by original source SHA.

## Feature Diagnostics fixes

- Reads live `session.active_mat` (no stale project-only field).
- Empty-state panel with RU/EN steps + actions (not modal-only).
- Separate prerequisite messages (project / active MAT / missing path / variable / frame / profile / contract).
- Confirmation summary before “Run V2 (shadow)”.
- Subscribes to project / active MAT / frame / profile / inventory / detach / cache-rebuilt events.

## Localization

Russian mode uses «Сначала откройте проект и выберите активный исходный MAT-файл.» and the other specified RU strings. Page + source card retranslate on language switch.

## Files changed (primary)

- `src/ionogram_morphology_lab/ui/active_source.py` (new)
- `src/ionogram_morphology_lab/ui/session.py`
- `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py`
- `src/ionogram_morphology_lab/ui/main_window.py`
- `src/ionogram_morphology_lab/projects/model.py`
- `tests/test_phase4b2c_active_source.py` (new)
- `docs/PHASE4B2C_ACCEPTANCE_REPORT.md` (this file)

## Tests

- `tests/test_phase4b2c_active_source.py`: **20 passed**
- Full repository suite: **247 passed**
- Validators: `validate_feature_shadow_mode` OK; `validate_feature_registry_v2` OK (93); `validate_synthetic_geometry_v2` OK (17/17, `iml2-0.2.0`); `validate_i18n` OK; `validate_version_consistency` OK

## Packaged EXE SHA-256

`BF3A27982EEB317AD61FDFFE04788CE7947225E1A9392A03ACE9FA25F377AAFE`

Path: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Explicit non-claims

- No scientific validation claimed.
- No morphology accuracy improvement claimed.
- Feature Pipeline V2 measurements/thresholds not changed in this phase.
- V2 not enabled by default.
