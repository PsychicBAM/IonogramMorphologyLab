# PHASE 4C.1e.3a — CI Repository Hygiene Hotfix Report

**Phase:** CI Repository Hygiene, Missing Documentation Fixture, Portable Paths, Security Finding Audit
**Prior commit:** `6fc7de0a03cb640f40622af15a17bcb1bf7095f5`
**Prior Build Identity:** `4C.1e.3`
**New Build Identity:** `4C.1e.3a`
**Prior EXE SHA-256:** `F8690809606B013E5A51A52564FBF1A8994FE06C4F1B42AF9DE6A4B65EF03CFE`
**Mode:** shadow-only
**Date:** 2026-08-05

## Original GitHub CI failures

A. Repository hygiene (`total_violations: 8`):

- `possible_secret: 1` -> `src/ionogram_morphology_lab/ui/main_window.py`
- `absolute_local_path: 7` -> seven documentation files (listed below)

B. Pytest on Linux:

- `520 passed`, `2 skipped`, `1 failed`
- Failure: `tests/test_phase3c_docs.py::test_control_reference_has_phase3b_rows`
- Missing file: `docs/_control_reference_phase3c.json`

## Missing fixture root cause

Outcome **C + B**:

- The fixture existed locally after Phase 3C generation but was **never tracked** in Git.
- The prior Phase 4C.1e commit staging intentionally avoided broad `docs/_*` dumps, and this product fixture was omitted with them.
- Git history has no prior commit of the path (`git log --follow` empty).
- Authoritative generator: `scripts/update_user_guide_controls_phase3c.py` (`CONTROLS` -> JSON).

## How `_control_reference_phase3c.json` was restored

1. Confirmed local file matched USER_GUIDE control-table row count (**67**).
2. Regenerated deterministically from `CONTROLS` in the generator script (JSON only; USER_GUIDE not rewritten).
3. Payload: `{"count": 67, "en_labels": [...]}` UTF-8, stable key order, no absolute paths, no secrets.
4. Tracked the file in Git.
5. `.gitignore`: **no ignore** of this fixture (and no need for a negation exception). Temporary dumps (`docs/_fd_*`, `docs/_phase4b*`, etc.) remain ignored separately.

`git check-ignore` -> not ignored.
`git ls-files docs/_control_reference_phase3c.json` -> tracked after staging.

## Seven documentation path corrections

| File | Change |
|---|---|
| `docs/ARCHIVE_VARIABLE_AUDIT_4A1.md` | Owner archive roots -> `<OWNER_ARCHIVE_ROOT>/...` |
| `docs/FEATURE_DIAGNOSTICS_REAL_ARCHIVE_PERFORMANCE.md` | Archive MAT paths -> `<OWNER_ARCHIVE_ROOT>/...` |
| `docs/PHASE4B2J_ACCEPTANCE_REPORT.md` | Leaked pytest cache path -> `<TEMP>/pytest-of-<user>/...` |
| `docs/PHASE4B2K_ACCEPTANCE_REPORT.md` | User AppData cache -> `%LOCALAPPDATA%/IonogramMorphologyLab/cache` |
| `docs/PHASE4C1E1_OWNER_VERIFICATION.md` | Project root / `Set-Location` / EXE -> `<PROJECT_ROOT>` and relative `dist/...` |
| `docs/PHASE4C1E2D_ACCEPTANCE_REPORT.md` | EXE path -> `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| `docs/PHASE4C1E3_ACCEPTANCE_REPORT.md` | EXE path -> `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |

Hygiene after fix: `absolute_local_path: 0`.

## Possible-secret root cause

**False positive — not a real credential.**

Detector: assignment-like literals whose left-hand names include common credential words
(`api_key` / `secret` / `token` / `password`) paired with a quoted string of length ≥ 8.

Match was a morphology taxonomy assignment used to prefill an expert-decision combo box
(codes such as `indeterminate` / `not_assessable`). The left-hand name looked like a
credential keyword to the scanner; the value is a public taxonomy code, not a secret.

**Action:** rename local variable to `morph_code` and clarify with a comment that it is a taxonomy code, not an API credential.

No credential rotation required.
No history rewrite.
No global scanner weaken / file exclude.

Hygiene after fix: `possible_secret: 0`.

## Linux portability audit

- Restored fixture is repository-relative and case-stable.
- Docs no longer embed Windows drive / user home absolute paths.
- No scientific path logic changed.
- Full pytest (`python -m pytest` and `python -m pytest tests -q`) green on Windows; fixture availability matches Linux CI expectation.

## Focused test results

```text
python scripts/check_repository_hygiene.py
-> total_violations: 0

python -m pytest tests/test_phase3c_docs.py -q
-> 6 passed in 3.73s
```

## Full pytest

```text
python -m pytest tests -q
523 passed in 364.28s (0:06:04)

python -m pytest
523 passed in 354.09s (0:05:54)
```

- Failed: **0**
- Errors: **0**
- Skipped: **0** (local Windows run; CI may still skip 2 platform-specific tests)
- Warnings: **0**

## Validators + hygiene

| Check | Result |
|---|---|
| Feature Registry | 93/93 |
| Synthetic Geometry | 17/17 |
| V2 shadow | OK |
| Morphology candidate shadow | OK |
| i18n | OK |
| docs | passed |
| repository hygiene | **0 violations** |

## Build Identity

| Field | Value |
|---|---|
| Phase | `4C.1e.3a` |
| Geometry | `iml2-0.2.0` |
| Candidate engine | `iml-morph-candidate-0.1.1` |
| Candidate / ledger schema | `2` / `2` |
| Ruleset | `iml-morph-candidate-rules 0.1.0` |
| Diagnostics layout schema | `2` |
| Sequence-state contract | `1` |
| Mode | shadow-only |

Frozen PYZ confirmed: `4C.1e.3a`.

## Packaging

```text
powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1
-> OK
```

**EXE path:** `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## New SHA-256

```text
C2CBE0182251C302B2A07E130E4423F316B7500AB508CA867C84EE8B04631652
```

Differs from prior `F8690809606B013E5A51A52564FBF1A8994FE06C4F1B42AF9DE6A4B65EF03CFE`.

## Packaged smoke results

| Check | Result |
|---|---|
| Launch / Responding | **PASS** |
| `--smoke-test` | **PASS** |
| Frozen Build Identity `4C.1e.3a` | **PASS** |
| V2 worker child spawn | **PASS** |
| Layers / Ctrl+0 / Commands / Follow / Sequence table / Sequence auto-candidate / single-frame manual candidate / Cancel | **PASS (contract)** via existing Phase 4C.1e suites; live GUI chrome still owner-confirmable in interactive session |

## Files changed (hotfix)

| Path |
|---|
| `docs/_control_reference_phase3c.json` *(restored / tracked)* |
| `docs/ARCHIVE_VARIABLE_AUDIT_4A1.md` |
| `docs/FEATURE_DIAGNOSTICS_REAL_ARCHIVE_PERFORMANCE.md` |
| `docs/PHASE4B2J_ACCEPTANCE_REPORT.md` |
| `docs/PHASE4B2K_ACCEPTANCE_REPORT.md` |
| `docs/PHASE4C1E1_OWNER_VERIFICATION.md` |
| `docs/PHASE4C1E2D_ACCEPTANCE_REPORT.md` |
| `docs/PHASE4C1E3_ACCEPTANCE_REPORT.md` |
| `docs/PHASE4C1E3A_CI_HOTFIX_REPORT.md` *(this file)* |
| `src/ionogram_morphology_lab/ui/main_window.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `tests/test_phase4c1e_layout_sequence_state.py` |
| `tests/test_phase4c1e2_sequence_follow.py` |
| `tests/test_phase4c1e3_sequence_table_readability.py` |
| `.gitignore` |

## Scientific non-claims

- No V2 / geometry / candidate rule or threshold changes.
- No Sequence Follow or Sequence-only automatic candidate behaviour changes.
- No single-frame manual candidate workflow changes.
- No production RuleEngine wiring.
- No Phase 4C.2 work.

## Git / CI (filled after push)

- Commit / push results recorded in the final agent summary after `git push origin main`.
- Local `HEAD` must equal `origin/main` after push.
- GitHub CI monitored via `gh` when available.
