# Phase 4C.4a Acceptance Report

**Build Identity:** `4C.4a`
**Mode:** shadow-only
**Date:** 2026-08-05
**Starting release commit:** `4738c5763aa7d65b52b4bd0ed4d10cfef9727183`
**Branch:** `phase/4c4a-disagreement-analysis`
**EXE SHA-256:** `EC5127E839BCBD7E0C07623B360B1E068D697DDE5B9F782FED0D8F2B2C516417`
**Git:** no commit, no push

## Scientific purpose

Read-only analytical layer above completed/revealed expert review corpora and campaigns. Descriptive questions only (transition counts, strata, hypotheses, decision gate). Neither expert nor candidate is treated as ground truth.

## Delivered

- Immutable analysis snapshots under `{project}/review_dataset/morphology_analyses/<id>/`
- Eligibility with explicit exclusion denominators
- Candidate engine/ruleset version stratification warnings
- Descriptive dashboard + Expertâ†’Candidate transition matrix (not a confusion/accuracy matrix)
- Case explorer (post-reveal / frozen analysis only)
- Append-only analyst hypotheses (do not alter labels/counts)
- Development-exposed contamination tracking
- Holdout planning with overlap checks; Outcome F requires untouched holdout plan
- Ruleset Decision Gate outcomes Aâ€“F
- Exports (MD/JSON/CSV) without absolute owner paths
- UI navigation EN â€œDisagreement Analysisâ€ / RU Â«ÐÐ½Ð°Ð»Ð¸Ð· Ñ€Ð°ÑÑ…Ð¾Ð¶Ð´ÐµÐ½Ð¸Ð¹Â»
- Background freeze worker with progress/cancel
- Validator `scripts/validate_morphology_disagreement_analysis.py`
- Focused tests `tests/test_phase4c4a_disagreement_analysis.py`
- Help topic Â§88 Disagreement Analysis

## Scientific contracts preserved

- shadow-only; scientifically_validated = false
- production RuleEngine unwired
- Geometry `iml2-0.2.0`; candidate engine `iml-morph-candidate-0.1.1`; ruleset `iml-morph-candidate-rules` / `0.1.0`
- no threshold tuning / training / accuracy-F1 claims
- blind corpora rejected; no candidate leakage into blind views
- frozen analysis does not silently mutate after source corrections

## Verification

| Gate | Result |
|------|--------|
| Full pytest | **708 passed**, 0 failed, 0 skipped (~8m01s) |
| Focused 4C.4a tests | **13 passed** |
| Focused warning audit | pytest-asyncio config deprecation only (pre-existing plugin) |
| Feature registry | **93/93** |
| Synthetic geometry | **17/17** (`iml2-0.2.0`) |
| Feature / candidate shadow | **OK** |
| Corpus / campaign validators | **OK** |
| Disagreement analysis validator | **OK** |
| i18n / docs | **OK / PASS** |
| Repository hygiene | **0 violations** |
| Packaged EXE start | **OK** |
| Domain smoke (synthetic) | **OK** â€” freeze, 5 disagreements / 1 match, small-sample warning, exposed holdout rejected, Decision Gate F + export, integrity OK |

### Suite note

`tests/test_viewer_slider_safety.py::test_duplicate_cache_build_rejected` previously left a phantom `QThread.isRunning()` true and hung session teardown. Cleared the fake worker after assertions (test-only fix; not a product change).

## Limitations

- Pilot descriptive workspace only
- Small samples show descriptive-only warning
- Outcome F authorizes a future proposal phase only; does not change candidate rules
- Interactive RU wizard path in packaged EXE deferred to owner visual QA

## No commit / no push
