# PHASE 4C.1e.2a Acceptance Report

**Phase:** Qt Test Harness Alignment, Lazy Features Empty-State Regression Repair, and Sequence Frame Preconditions  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.2` (unchanged)  
**Mode:** shadow-only  
**Date:** 2026-08-04  

## Owner test result

Owner verification after Phase 4C.1e.2:

- **486 passed**
- **4 failed**
- **9 sklearn warnings** (unrelated; not addressed in this phase)

All validators passed:

- Feature Registry: 93/93  
- Synthetic Geometry: 17/17  
- V2 shadow isolation: OK  
- Morphology candidate shadow: OK  
- i18n: OK  
- docs: OK  

## Analysis of each failure

| # | Test | Root cause | Correction |
|---|---|---|---|
| 1 | `test_fd_constructor_creates_skeleton_only` | Stale expectation that Features `QTableView` must be visibly shown after `_ensure_features_tab()`. Lazy empty-state UX intentionally hides the table when no V2 result is bound. | Assert model/view existence, empty-state label, legacy list hidden, and either table-or-empty presentation — not forced table visibility. |
| 2 | `test_other_frame_result_does_not_overwrite_manual_selection` | `_enter_sequence(..., current=10)` set the spin before ensuring its range covered frame 10. After synthetic-source refresh, `QSpinBox` maximum can be 1, so Qt clamped value to 1. | Expand spin/slider/`_n_frames` maxima from `frames + [current]` before `setValue`; assert precondition `frame_spin.value() == 10`. |
| 3 | `test_features_empty_state_pending_on_page` | Used `QWidget.isVisible()`, which is false when any ancestor (inactive Features tab) is not visible — even when the label is explicitly shown. | Unit-level: assert `isHidden() is False` + table `isHidden() is True` + localized text. |
| 4 | `test_pending_row_does_not_rerun_v2` | Same inactive-tab `isVisible()` semantics. | Same Option B assertions; keep zero `run_shadow` calls. |

## Stale skeleton-test expectation

`test_fd_constructor_creates_skeleton_only` must keep proving skeleton-first construction and deferred Features/Review/Tech/Help/Layers. It must **not** require the Features table to be displayed when no compatible V2 result exists. Valid presentation after `_ensure_features_tab()` with no result: empty-state label unhidden, table hidden.

## QSpinBox frame-range setup issue

Synthetic inventory refresh can set `_n_frames` / spin maximum below sequence test frames (e.g. max=1). Setting `frame_spin` to 10 then silently becomes 1. Helper `_ensure_frame_spin_range` + post-set assertion fail loudly at setup if the requested frame cannot be selected. Production navigation was not changed.

## Inactive-tab `isVisible()` semantics

`isVisible()` requires the widget and all parents to be visible. An inactive `QTabWidget` page makes children report not visible even after `show()`. Tests now:

- **Option B** (unit): `isHidden()` / text / model row count  
- **Option A** (UX regression): activate Features tab, `processEvents`, then assert `isVisible()` for pending → hydrated swap  

## Production empty-state audit

Reviewed `_update_features_empty_state()` / `_ensure_features_tab()` / `_populate_features()`:

| Condition | Empty label | Features view | Notes |
|---|---|---|---|
| Pending current sequence frame | shown + pending text | hidden | no V2 rerun |
| Outside selected sequence | shown + outside text | hidden | follow UI actions updated |
| Hydrating | shown + hydrating text | hidden while hydrating | |
| Failed | shown + failure text | hidden | |
| Legacy incomplete | legacy message | hidden | |
| No applicable features | not_applicable text | hidden | not a blank table |
| Compatible populated result | hidden | shown | model rows present |

No production empty-state behaviour was weakened to satisfy stale visibility assumptions. No scientific result is synthesized from an empty state.

## Files changed

| Path |
|---|
| `tests/test_phase4b2j_cache_and_retranslate.py` |
| `tests/test_phase4c1e2_sequence_follow.py` |
| `docs/PHASE4C1E2A_ACCEPTANCE_REPORT.md` *(this file)* |

Production UI/science modules were audited; **no production source edits** were required for this harness alignment.

## Tests changed but not run

Updated:

- skeleton Features presentation contract  
- `_enter_sequence` / `_ensure_frame_spin_range`  
- manual-selection frame precondition  
- empty-state `isHidden` assertions  
- pending row zero V2 reruns  

Added:

- `test_active_features_tab_pending_then_hydrated`  
- `test_enter_sequence_configures_valid_frame_range`  

**This session did not execute pytest, validators, linters, builds, packaging, or SHA commands.**

## No EXE / no SHA

- No EXE was built.  
- No SHA-256 was calculated.  

## Scientific non-claims

This phase does not claim:

- V2 / geometry / candidate threshold changes  
- RuleEngine or production enablement  
- that tests or packaging passed  
- removal of sklearn warnings  

## Owner re-verification commands

Suggested (owner-run only):

```text
pytest tests/test_phase4b2j_cache_and_retranslate.py::test_fd_constructor_creates_skeleton_only -q
pytest tests/test_phase4c1e2_sequence_follow.py -q
pytest -q
```

Then re-check the previous validator suite if desired. Do not begin Phase 4C.2 until these four failures are cleared by owner verification.
