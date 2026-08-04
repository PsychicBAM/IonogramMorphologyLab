# PHASE 4C.1e.2c Acceptance Report

**Phase:** Features Identity Navigation Contract and Final Pytest Closure  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.2c`  
**Mode:** shadow-only  
**Date:** 2026-08-04  

## Owner result

After Phase 4C.1e.2b:

- **497 passed**
- **1 failed**
- **9 unrelated sklearn warnings**

Failing test: `test_features_identity_line_updates_per_selected_row`.

## Why the test’s `_loaded_frame` assignment violated the navigation contract

The test did:

```python
page.frame_spin.setValue(20)
page._loaded_frame = 20
page._update_features_identity_line()
```

After 4C.1e.2b, Features identity uses **`_intended_frame`** (`_authoritative_frame()`), not `_loaded_frame`. Assigning `_loaded_frame` is not a navigation event and must not change identity. `setValue(20)` alone only queues the spin debounce (`valueChanged` → `_on_frame_spin`); without `_commit_spin_edit` / debounce completion / `_goto_frame`, `_intended_frame` remained **10**, so identity correctly stayed on frame 10.

## Audit result: real frame-spin signal wiring

| Step | Handler | Contract |
|---|---|---|
| `frame_spin.valueChanged` | `_on_frame_spin` | Syncs slider preview; starts 300 ms debounce |
| debounce timeout | `_apply_debounced_spin` | `_goto_frame(..., reason="user_frame_entry")` |
| `editingFinished` | `_commit_spin_edit` | Immediate `_goto_frame(..., reason="user_frame_entry")` |
| `_goto_frame` | bump nav gen, intended frame, spin+slider, pause Follow, schedule load, **refresh Features identity/empty state** |

Stale frame-1/frame-10 load completions remain discarded by navigation-generation guards from 4C.1e.2b.

## Authoritative identity-frame rule

1. **Pending / hydrating:** identity uses intended/selected frame.  
2. **Compatible bound result:** may confirm the same frame when `result.frame_index == intended` and source SHA matches.  
3. **Never:** stale `_loaded_frame`, last-finished async load, or mismatched result frame.  
4. Stale/mismatched result status is not shown as V2 cached/ready for the current intended frame.

## Production corrections

| Change | Purpose |
|---|---|
| `_goto_frame` always calls `_update_features_identity_line` / `_update_features_empty_state` | Identity follows intent immediately, before load completes |
| `_commit_spin_edit` / `_apply_debounced_spin` pass `reason="user_frame_entry"` | Explicit navigation reason |
| `_update_features_identity_line` matching-result gate | Ready/cached labels only when result frame+source match intended |

Stale-callback guards were not weakened. Follow-processing behaviour unchanged.

## Test corrections

- `test_features_identity_line_updates_per_selected_row` — uses `_goto_frame(20, …)`; asserts intended/spin/slider/nav-gen/Follow pause; no `_loaded_frame` mutation as navigation.  
- Added `test_user_spin_navigation_updates_intended_and_identity` — real `setValue` + `_commit_spin_edit`.  
- Added `test_result_hydration_identity_ignores_stale_other_frame`.  
- Added `test_manual_frame_change_pauses_follow_resume_restores`.  
- Build Identity assertions → `4C.1e.2c`.

## Files changed

| Path |
|---|
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `tests/test_phase4c1e2_sequence_follow.py` |
| `tests/test_phase4c1e_layout_sequence_state.py` |
| `docs/PHASE4C1E2C_ACCEPTANCE_REPORT.md` *(this file)* |

## Tests added but not run

This session did **not** execute pytest, validators, linters, builds, packaging, or SHA commands.

## No EXE / no SHA

- No EXE built.  
- No SHA-256 calculated.  

## Scientific non-claims

No V2/geometry/candidate threshold or RuleEngine changes. No production enablement. No claim that tests passed in this session.

## Owner re-verification commands

```text
pytest tests/test_phase4c1e2_sequence_follow.py::test_features_identity_line_updates_per_selected_row -q
pytest tests/test_phase4c1e2_sequence_follow.py::test_user_spin_navigation_updates_intended_and_identity -q
pytest tests/test_phase4c1e2_sequence_follow.py::test_result_hydration_identity_ignores_stale_other_frame -q
pytest tests/test_phase4c1e2_sequence_follow.py -q
pytest -q
```

Do not begin Phase 4C.2 until owner accepts this closure.
