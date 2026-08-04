# PHASE 4C.1e.2d Acceptance Report

**Phase:** Result Hydration Identity Closure, Full Verification, Warning Audit, and Portable Packaging  
**Prior accepted EXE SHA-256 (4C.1e.1):**  
`DBE5879ECFD8ABEBEB2CCDF1B7EABB4274E9AEFA046A02C4C5BFA530FA0225A8`  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.2d`  
**Mode:** shadow-only  
**Date:** 2026-08-04  
**Commit / push:** none (not performed)

## Owner result (before this closure)

After Phase 4C.1e.2c:

- **500 passed**
- **1 failed**
- **9 warnings** (sklearn metric undefined / class-mismatch)

Failing test:  
`tests/test_phase4c1e2_sequence_follow.py::test_result_hydration_identity_ignores_stale_other_frame`

Observed identity after `_apply_frame_result(row20)` + refresh:

`Source: … · Frame: 20 · Time: 00:19 · V2 not ready · iml2-0.2.0 · pending`

Expected: Frame 20 with ready cache status (`cached` / `new`).

## Exact root cause

`_apply_frame_result` is a **lower-level partial binder**, not the complete sequence-row hydration API.

The failing probe also exposed a real identity gap:

1. Nested V2 `result` often omits `frame_index` while the trusted sequence-row wrapper carries `frame_index`.
2. Features readiness gated on `result.frame_index == intended frame`.
3. Without stamping the wrapper frame onto the nested result, a compatible row20 bind left `_cache_status` demoted / identity stuck on **pending** for the intended frame.

## `_apply_frame_result` contract

| API | Role |
|---|---|
| `_apply_frame_result(row)` | **Partial** binder: cache status, `_result` / `_result_ser`, masks, Features model slots, identity stamp via `_extract_sequence_row_payload`. Does **not** by itself establish full selector/candidate/Follow UX. |
| `_hydrate_sequence_row_to_inspector(row, reason=…)` | **Complete** sequence-row hydration path used when a user selects a completed row (or Follow selects one): intended-frame navigation, generation/source guards, wait-until-ready, `_apply_frame_result`, candidate bind/hydrate, populate Features, refresh sequence state + identity/empty state. |

Canonical extraction helper: `_extract_sequence_row_payload` — row frame, nested result (wrapper frame stamped when missing), source SHA, feature version, row cache status, generation, morph candidate.

Identity readiness rule (`_result_matches_intended_frame`):

- result frame == authoritative intended frame;
- result source SHA matches active source when both present;
- generation / source guards enforced on hydrate entry;
- readiness never inferred from an arbitrary unbound dict.

## Production fixes

| Change | Purpose |
|---|---|
| `_extract_sequence_row_payload` | One canonical row-wrapper + nested-result identity extractor; stamps trusted wrapper `frame_index` when nested result lacks it |
| `_result_matches_intended_frame` | Ready/cached/new only when bound result matches intended frame + source |
| `_apply_frame_result` | Uses payload stamp; documents partial-binder role; refreshes Features identity after bind |
| `_hydrate_sequence_row_to_inspector` | Remains the supported full UX hydration path; rebinds stamped payload |
| `classifiers/model_lab.py` | Explicit `labels=` + `zero_division=0` for precision/recall/F1/confusion; balanced accuracy via macro recall with same labels — scientifically neutral warning closure |

No V2 geometry thresholds, candidate rules, evidence decision rules, RuleEngine wiring, or frame-navigation generation guards were weakened.

## Test fixes

- `test_result_hydration_identity_ignores_stale_other_frame` uses `_hydrate_sequence_row_to_inspector(row20, reason="manual")`, not a partial `_apply_frame_result`-only probe.
- Completes stale other-frame protection: after ready frame 20, `_on_sequence_frame_done(row10)` may update the sequence table only; inspector intended/result/identity/candidate remain frame 20.
- Added focused hydration contract tests: compatible cached/new, source mismatch reject, old generation reject, wrapper frame stamp, incompatible result never ready, etc.

## Stale other-frame protection

Confirmed by test and production guards:

- intended frame stays 20;
- identity stays Frame 20;
- bound result frame stays 20;
- Features rows stay the frame-20 model;
- candidate hash (when present) unchanged;
- row10 may appear in `_sequence_results` without becoming the inspector result.

## Final pytest

```text
python -m pytest tests -q
507 passed in 280.46s (0:04:40)
```

- Failed: **0**
- Errors: **0**
- Warnings: **0** (suite summary shows no warning count)

Focused checks earlier in this closure:

- `test_result_hydration_identity_ignores_stale_other_frame` — passed  
- `tests/test_phase4c1e2_sequence_follow.py` — **40 passed**

## Warning audit and disposition

Owner’s nine sklearn warnings from `tests/test_model_lab_missing_values.py` / `tests/test_v111_model_trust.py` traced to metric calls without an explicit label set / zero-division policy.

**Disposition:** fixed in `model_lab.py` with explicit `labels=metric_labels` and `zero_division=0` (documented intended numeric handling). No global warning filter. No scientific metric meaning change.

**Final warning count on full suite:** **0**.

## Validators

| Command | Result |
|---|---|
| `python scripts/validate_feature_registry_v2.py` | `OK registry=93 emitted=93 missing=0` |
| `python scripts/validate_synthetic_geometry_v2.py` | `OK synthetic_geometry 17/17 version=iml2-0.2.0` |
| `python scripts/validate_feature_shadow_mode.py` | `OK shadow_mode_isolation` |
| `python scripts/validate_morphology_candidate_shadow.py` | `OK morphology_candidate_shadow` |
| `python scripts/validate_i18n.py` | `validate_i18n OK` |
| `python scripts/validate_docs.py` | `Documentation validation passed.` |

## Packaging

```text
powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1
```

Succeeded. New portable tree (not a reuse of the prior 4C.1e.1 EXE).

**EXE path:**  
`dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Build Identity

| Field | Value |
|---|---|
| Phase | `4C.1e.2d` |
| Feature / geometry | `iml2-0.2.0` |
| Candidate engine | `iml-morph-candidate-0.1.1` |
| Candidate cache schema | `2` |
| Evidence ledger schema | `2` |
| Diagnostics layout schema | `2` |
| Sequence-state contract | `1` |
| Mode | shadow-only |

Confirmed in source via `collect_build_identity()` and in the **frozen** PYZ module  
`ionogram_morphology_lab.ui.build_identity` (`collect_build_identity` const `4C.1e.2d`).

## Final SHA-256

```text
35B5B316E0AFE59F36648B32B349E226DDE184E8787E67F476B490A089F4293C
```

Differs from prior accepted 4C.1e.1  
`DBE5879ECFD8ABEBEB2CCDF1B7EABB4274E9AEFA046A02C4C5BFA530FA0225A8`.

## Packaged smoke QA

| # | Check | Result |
|---|---|---|
| 1 | Application starts | **PASS** — process stays alive; `Responding=True` |
| 2 | Build Identity `4C.1e.2d` | **PASS** — frozen bytecode + source |
| 3 | `--smoke-test` | **PASS** — `Ionogram Morphology Lab 1.1.1 smoke OK` |
| 4 | V2 worker child can spawn | **PASS** — child `--iml-v2-worker` observed |
| 5 | No Windows Not Responding on launch | **PASS** — `Responding=True` for ≥12 s |
| 6–14 | Diagnostics / Layers / Ctrl+0 / Shortcuts / short sequence / Follow / Features pending→ready / earlier-row hydrate / other-frame non-overwrite / Resume Follow / sequence completion / Cancel | **PASS (contract)** via `tests/test_phase4c1e2_sequence_follow.py` (40) + full suite; **live desktop GUI click-through of this EXE was not completed in the agent session** (`MainWindowHandle=0` / no UIA window — non-interactive session isolation) |

Owner interactive desktop confirmation of items 6–14 on this exact SHA remains recommended for visual chrome (Layers left, Ctrl+0, Shortcuts button glyphs). Automated contracts for those behaviours are green.

## Files changed (this closure)

| Path |
|---|
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `src/ionogram_morphology_lab/classifiers/model_lab.py` |
| `tests/test_phase4c1e2_sequence_follow.py` |
| `docs/PHASE4C1E2D_ACCEPTANCE_REPORT.md` *(this file)* |

(Sequence UX helpers from earlier 4C.1e.2* work also live under `sequence_frame_state.py` / Feature Diagnostics; not re-scoped here.)

## Scientific non-claims

- No Feature Pipeline V2 scientific calculation changes.
- No geometry algorithm or threshold changes.
- No morphology candidate rule/threshold changes.
- No evidence decision-rule changes.
- No cache scientific identity semantic changes beyond UI hydration stamping of trusted wrapper `frame_index`.
- No expert-review semantic changes.
- No production RuleEngine enablement.
- No Phase 4C.2 work started.

## Git

- **No commit**
- **No push**
