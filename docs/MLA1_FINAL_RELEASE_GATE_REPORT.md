# ML-A.1 → ML-A.1a.2 — Final Release Gate Report

**Branch:** `phase/ml-a1-dataset-readiness`
**Date:** 2026-08-06
**Mode:** Shadow-only. No commit. No push.
**Owner visual QA:** **PASS** (confirmed for packaged ML-A.1a.2)

## Accepted phases

| Phase | Scope |
| --- | --- |
| **ML-A.1** | Dataset readiness domain, UI, Gate, holdout feasibility, no-training posture |
| **ML-A.1a** | RU/EN localization, saved-audit auto-reload, source/date projection, task-contract coverage, export ≠ audit create |
| **ML-A.1a.1** | Acquisition-date authority order, filename `Am_all_2014-10-15.mat` → `2014-10-15`, legacy audit warn + corrected revision |
| **ML-A.1a.2** | Worker progress completion lifecycle (success @ 100%, cancel/fail safe, no lingering QThread) |

## Owner visual QA

**PASS.** Owner confirmed:

- RU/EN readiness UI; saved audits auto-load; export does not duplicate audits
- Task-contract-specific coverage; source identity + acquisition date correct
- `Am_all_2014-10-15.mat` → `2014-10-15`; 13 frames → `unique_source_dates = 1`
- Frame times separate; legacy invalid audits warn; corrected revisions preserve parent
- Readiness Gate works; freeze finishes at 100%; Cancel disabled after success
- No Windows Not Responding; no lingering worker/QThread

## Full pytest

Command: `python -m pytest`

### First full run (before gate fix)

- **1 failed**, 768 passed
- Failure: `tests/test_mla1_dataset_readiness.py::test_worker_cancel_and_teardown`
- Root cause: test still constructed `FreezeReadinessWorker(store, corpus, audit_id)` after ML-A.1a.2 keyword-only worker API change
- Fix: **test-only** update to `mode=` / `audit_id=` kwargs
- **No product source change.** No EXE rebuild. Build Identity remains **ML-A.1a.2**.

### Second full run (release gate)

```
769 passed in 449.29s (0:07:29)
```

| Metric | Result |
| --- | --- |
| Passed | **769** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** (none reported) |
| Unexpected xpass | **0** |
| Warnings | Quiet mode (`-q`) did not emit a suite-level warning summary. Prior focused `-W default` runs showed only the pre-existing `pytest-asyncio` `asyncio_default_fixture_loop_scope` deprecation (environment), not new product warnings from this gate fix. |

## Validators

| Validator | Result |
| --- | --- |
| `validate_feature_registry_v2.py` | **OK registry=93/93** |
| `validate_synthetic_geometry_v2.py` | **OK 17/17** (`iml2-0.2.0`) |
| `validate_feature_shadow_mode.py` | **OK** |
| `validate_morphology_candidate_shadow.py` | **OK** |
| `validate_morphology_review_corpus.py` | **OK** |
| `validate_morphology_review_campaign.py` | **OK** |
| `validate_morphology_disagreement_analysis.py` | **OK** (`iml-disagreement-analysis-0.1.0`) |
| `validate_ml_dataset_readiness.py` | **OK** (`iml-ml-dataset-readiness-0.1.0`; 13 prohibited metrics guarded) |
| `validate_i18n.py` | **OK** |
| `validate_docs.py` | **PASS** |
| `check_repository_hygiene.py` | **0 violations** |

Validators were not weakened.

## Scientific contract audit

| Contract | Status |
| --- | --- |
| Shadow-only posture active (`shadow_only=True`) | PASS |
| `scientifically_validated=False` | PASS |
| No ML training added | PASS |
| No ML runtime dependency added in readiness package | PASS |
| Production RuleEngine remains unwired | PASS (readiness is audit/governance only) |
| Candidate / geometry scientific versions unchanged (`iml2-0.2.0` geometry validator; candidate engine still reported via Build Identity) | PASS |
| Readiness protocol `iml-ml-dataset-readiness-0.1.0` | PASS |
| Disagreement protocol `iml-disagreement-analysis-0.1.0` | PASS |
| Candidate labels excluded from expert target distributions (integrity leakage checks) | PASS |
| Corrected reviews not independent second opinions (review note + independence accounting) | PASS |
| Development-exposed items cannot enter untouched holdout | PASS |
| Related-frame groups / sequences not randomly split | PASS |
| Holdout Feasibility = assessment only | PASS |
| Outcome F → ML-B planning only; `authorizes_training=False` always | PASS |
| No accuracy/F1/sensitivity/specificity claims | PASS (prohibited metrics guarded) |
| No absolute owner paths in exports | PASS (hygiene + export path stripping) |

## Regression hotspot audit

| Hotspot | Status |
| --- | --- |
| Saved audits load independently of corpus selection | PASS (owner QA + tests) |
| Export does not create audit IDs | PASS |
| Frozen audits restore own task contract | PASS |
| Source/date never uses `frame_time` as acquisition date | PASS |
| `Am_all_2014-10-15.mat` → `2014-10-15` | PASS |
| `unique_source_dates` counts normalized dates | PASS |
| Legacy invalid frozen audits immutable | PASS |
| Corrected revision gets new audit identity | PASS |
| Success status cannot coexist with progress &lt; 100% | PASS |
| Cancellation/failure cannot appear as success | PASS |
| Duplicate finished signals ignored | PASS |
| No lingering QThread | PASS |
| Normal RU UI without raw canonical codes | PASS |
| Technical raw fields collapsed by default | PASS |

## Build and package status

| Item | Value |
| --- | --- |
| Build Identity | **ML-A.1a.2** (retained; no product fix required) |
| EXE path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` |
| Accepted / owner-verified SHA-256 | `67FBB83E6BCECF2A58C719A57AF5E60B9E74FCB31EB1FC130B8BD8DAE6A6A246` |
| On-disk SHA re-check | **matches** |
| Rebuild performed | **No** (test-only gate fix) |

## Git review

```
git rev-parse --abbrev-ref HEAD  →  phase/ml-a1-dataset-readiness
git status --short               →  modified + untracked (see lists)
git diff --check                 →  no whitespace errors (LF/CRLF warnings only)
```

**No staging performed. No commit. No push.**

### Intended commit inclusion (~48 paths)

Product / release content for ML-A.1…ML-A.1a.2:

- `src/ionogram_morphology_lab/ml_dataset_readiness/` (14 modules: domain, contracts, inventory, coverage, missingness, contamination/holdout, gate, acquisition date, exports, integrity, display labels, store)
- `src/ionogram_morphology_lab/ui/ml_data_readiness_page.py`
- `src/ionogram_morphology_lab/ui/main_window.py` (nav / page wiring)
- `src/ionogram_morphology_lab/ui/build_identity.py`
- `src/ionogram_morphology_lab/i18n/en.json`, `ru.json`
- `src/ionogram_morphology_lab/help/content.py`
- Build-identity bumps in corpus/campaign constants/models/exports/comments (phase label only)
- Identity assert updates in prior phase tests
- `scripts/validate_ml_dataset_readiness.py`
- `tests/test_mla1_dataset_readiness.py`
- `tests/test_mla1a_readiness_fixes.py`
- `tests/test_mla1a1_acquisition_date.py`
- `tests/test_mla1a2_progress_lifecycle.py`
- Docs: `MLA1_ACCEPTANCE_REPORT.md`, `MLA1A_ACCEPTANCE_REPORT.md`, `MLA1A1_ACCEPTANCE_REPORT.md`, `MLA1A2_ACCEPTANCE_REPORT.md`, `MLA1_OWNER_QA.md`, `MLA1_FINAL_RELEASE_GATE_REPORT.md`
- Related architecture / literature / decision-map / Phase4C4A doc cross-links
- `.gitignore` (readiness-related ignore if present)

### Explicit exclusions (do not stage)

- `config/user_settings.json`
- Owner MAT files / non-synthetic `*.mat`
- `review_dataset/` runtime data, saved readiness audits, generated exports
- Local databases / workspaces / caches
- `matlab_builtin/` churn
- `synthetic_data/*.mat` binary churn
- `matlab_studio_library/`, `model_lab/`, `user_library/`
- `src/ionogram_morphology_lab.egg-info/`
- `build/`, `dist/`
- Temporary / IDE / OS junk

## Release readiness

| Gate | Result |
| --- | --- |
| Owner visual QA | PASS |
| Full pytest | **769 passed**, 0 failed |
| All validators | PASS |
| Hygiene | **0** |
| Scientific contracts | PASS |
| Regression hotspots | PASS |
| Accepted package SHA | retained |
| Commit | **not performed** |
| Push | **not performed** |

**Verdict: READY FOR COMMIT/PUSH** when the owner explicitly authorizes staging of the inclusion list only (exclusions above remain out of the commit).
