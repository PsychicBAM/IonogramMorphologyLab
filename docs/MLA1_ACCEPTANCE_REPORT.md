# Phase ML-A.1 Acceptance Report

**Build Identity:** `ML-A.1`
**Mode:** shadow-only (audit and governance; no training)
**Date:** 2026-08-06
**Starting release commit:** `c0564bfe5ede8dd5346e16b320da5e874f846c0c`
**Branch:** `phase/ml-a1-dataset-readiness`
**EXE SHA-256:** `0743C25CEED236E38C9400DAB3FDD0910D469F4BD77743CAC82629947A694BFE`

The portable package was rebuilt after adding explicit readiness and
disagreement-analysis protocol version fields to Build Identity.

## Purpose

Implement a read-only dataset and label readiness layer that answers what expert-labelled data exist, which task contracts they can support, coverage/missingness/reviewer independence, contamination-aware holdout feasibility, and an ML-B readiness gate.

## Non-goals

- No model training
- No candidate/geometry threshold changes
- No TensorFlow / PyTorch / scikit-learn training dependencies
- No production RuleEngine wiring
- No accuracy / F1 / sensitivity / specificity / scientific validation / ground-truth claims
- No final train/development/holdout manifests (ML-B)
- No commit / no push in this implementation turn

## Delivered

- Package `src/ionogram_morphology_lab/ml_dataset_readiness/`
- UI page `ml_data_readiness_page.py` (Methods → ML Data Readiness)
- Task contracts A–D (morphology, assessability, interference, parameter scaling)
- Candidate-independent current-state inventory
- Coverage, missingness, reviewer independence, contamination
- Holdout feasibility assessment (not a holdout dataset)
- Readiness Gate A–F (F = ML-B planning only)
- Validator `scripts/validate_ml_dataset_readiness.py`
- Focused tests `tests/test_mla1_dataset_readiness.py`
- Help section 89; RU/EN i18n; gitignore for `ml_readiness/`
- Literature-audit cross-reference (ML-A stage now has an audit implementation path; still no training)
- Build Identity exposes `ml_dataset_readiness_protocol_version` and `disagreement_analysis_protocol_version`

## Expected small-pilot interpretation

A small pilot with concentrated mixed-spread labels, limited dates/sources, few independent second reviews, correlated adjacent frames, and development-exposed disagreement items should normally produce gate outcomes among A, C, D, or E. That is the scientifically correct result, not a software failure.

## Verification

| Check | Result |
|-------|--------|
| Focused ML-A.1 tests | **15 passed** (prior full implementation) |
| Focused identity refresh tests | **4 passed** |
| Full pytest | **723 passed** (prior; not re-run in package refresh) |
| Registry | **93/93** (prior) |
| Geometry | **17/17** (prior) |
| Shadow validators | **OK** (prior) |
| Corpus / campaign / disagreement / readiness validators | **OK** |
| i18n / docs / hygiene | **OK / PASS / 0** |
| Packaged smoke (protocol stamp refresh) | **PASS** — EXE starts, Responding; Technical Details shows ML-A.1 + both protocol versions; nav key present |
| Owner visual QA | **not claimed in this refresh** |

## Explicit non-actions

- Phase ML-B not started
- No literature PDFs copied into the repository
- No commit / no push
