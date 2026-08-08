# ML-C.1 → ML-C.1b Final Release Gate Report

**Branch:** `phase/ml-c1-offline-baselines`  
**Final Build Identity:** ML-C.1b  
**Accepted EXE SHA-256:** `1BA1E89E7B51C32992D7C3D00B807D4854EE2135DF5F25729CBA6322BDC3C484`  
**Protocol:** `iml-ml-offline-baselines-0.1.0`  
**Owner visual QA:** **PASS**  
**Gate result:** **GREEN**  
**Commit/push:** not performed (awaiting explicit owner request)

---

## Phase chain

| Phase | Focus | Outcome |
|-------|--------|---------|
| **ML-C.1** | Offline TRAIN-fit / DEVELOPMENT-eval baselines; holdout firewall; synthetic QA fixture | Accepted into chain |
| **ML-C.1a** | Primary Validate/Run UX; completed immutability; live RU/EN; no absolute path in header | Owner workflow/i18n PASS |
| **ML-C.1b** | Prediction label integrity (`mixed_spread`≠`m`); fail-closed invalid labels; N/A metrics UI; Error Analysis completeness | Owner Development Evaluation / Error Analysis PASS |

No product source was changed after owner-accepted ML-C.1b EXE.  
Full-pytest gate required **test-only** assertion updates (formatted build-identity substring `ML-B.1` → `ML-C.1b`). Build Identity and EXE SHA remain **ML-C.1b** / accepted hash above.

---

## Owner visual QA (PASS)

Confirmed by owner on accepted EXE:

- New Experiment creates/selects a draft; Validate visible; Run visible and disabled before validation; validation enables Run; run completes at 100%
- Completed experiments immutable; View / More / column controls work
- RU↔EN live translation; no mixed-language UI in inspected ML-C workflow
- Absolute runtime artifact path not shown as normal header status
- Majority Class predictions preserve complete canonical labels; no malformed `m` in new experiments
- Undefined development metrics render as N/A / Не определено
- Error Analysis fields populated; holdout SEALED / UNUSED; no item-level holdout labels/predictions
- Development Evaluation is development-only; owner accepted presentation

Historical malformed QA experiments containing prediction `m` remain untouched (may be reported as invalid historical QA).

---

## Full pytest (exact)

Command: `python -m pytest`

**Final green run:**

| Metric | Value |
|--------|-------|
| Collected | **890** |
| Passed | **890** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** |
| xfailed / xpassed | **0** / **0** |
| Duration | **569.10 s** (~9 m 29 s) |

**First full run (before test-only fix):** 886 passed, 2 failed, 2 errors (616.96 s).

- Failures: stale `assert "ML-B.1" in format_build_identity(...)` in  
  `tests/test_phase4c1e3_sequence_table_readability.py`,  
  `tests/test_phase4c1e_layout_sequence_state.py` → updated to `ML-C.1b` (tests only).
- Errors: transient `OSError` on `synthetic_data/demo_smooth_trace.mat` during module fixture rewrite; focused re-run passed without product change; full suite green on rerun.

Warnings: final green run summary showed no pytest warning/xfail section (0 unexpected xpass).

---

## Validators

| Validator | Result |
|-----------|--------|
| `validate_feature_registry_v2.py` | OK |
| `validate_synthetic_geometry_v2.py` | OK |
| `validate_feature_shadow_mode.py` | OK |
| `validate_morphology_candidate_shadow.py` | OK |
| `validate_morphology_review_corpus.py` | OK |
| `validate_morphology_review_campaign.py` | OK |
| `validate_morphology_disagreement_analysis.py` | OK |
| `validate_ml_dataset_readiness.py` | PASS |
| `validate_ml_dataset_manifests.py` | OK |
| `validate_ml_offline_baselines.py` | OK (WARN historical `m` experiments; not rewritten) |
| `validate_i18n.py` | OK |
| `validate_docs.py` | PASS |
| `check_repository_hygiene.py` | **0** violations |

---

## Scientific contract audit

All items **PASS** (evidence in `src/ionogram_morphology_lab/ml_offline_baselines/` + UI + tests):

- Fit TRAIN only; evaluation DEVELOPMENT only; TRAIN-only scaler; no DEVELOPMENT labels in fit; no post-eval train+dev refit
- Holdout sealed; no item-level holdout reference opens; no holdout frames/predictions/metrics; unused for normalization/balancing/tuning; absent from exposure ledger
- Features: candidate-independent pool16; 256 dims; deterministic; no RuleEngine/candidate/identity predictors; no temporal windows
- Baselines preserve full canonical labels; invalid predictions fail closed; malformed tokens cannot become CM axes
- Metrics DEVELOPMENT-only; explicit denominators; deterministic CM; overall agreement; macro F1; per-class; `null` in artifacts; UI N/A / Не определено; no fake zero; no holdout-performance / scientific-validation wording
- Completed immutable; revisions/new experiments; provenance/hashes; historical malformed QA not rewritten
- Production RuleEngine unwired to ML-C; **ML-D not started**; **ML-E not started**; no production deployment claim

### Root cause / fix of `mixed_spread` → `m`

`MajorityClassBaseline.predict` used `np.full(n, label, dtype=str)` → NumPy `<U1>` truncation.  
Fixed to object/full-string arrays; model artifact already stored full `majority_class`. Fixture was not the cause.

---

## Regression hotspot audit

### Scenario A — blocked real pilot

- Project without eligible frozen ML-B manifest: blocked with readable message; Run disabled; no random split / bypass  
- Covered by ML-C governance / UI tests and owner QA

### Scenario B — synthetic QA

Workspace: `workspaces/MLC1_Offline_Baselines_QA_8a22c20228f2`  
Manifest: `manifest_edd6e7a46b3c`  
Roles: TRAIN **18** / DEVELOPMENT **9** / holdout **9** aggregate items; holdout **SEALED / UNUSED**

| New experiment | Result |
|----------------|--------|
| Majority `mlc_21af3cb4c78e` | preds=`mixed_spread` (full); n=9; CM axes valid; overall=0.0; macro_f1=null → UI N/A |
| Nearest Centroid `mlc_d448ea6f8bb4` | valid labels; n=9; overall=1.0; macro_f1=1.0 |

UI: New/Validate/Run lifecycle; completed immutable; More/View localized; RU↔EN preserves state; Technical Details collapsed by default; no absolute path in normal header; Error Analysis populated; no holdout rows.

---

## Screenshots / README

- Gallery: `docs/assets/screenshots/ml-c1b/` — **24 PNG** (12 scenes × EN/RU), plus `CAPTURE_LOG.md` (does not overwrite `ml-b1d/` or `ml-a1a2/`)
- Capture script: `scripts/capture_mlc1b_screenshots.py` (Windows Qt + Segoe UI; synthetic QA only; corrected Majority/Centroid experiments)
- Screenshot allowlist: `scripts/validate_phase3c_docs.py` includes `ml-c1b`
- README EN/RU updated to ML-C.1b **release-ready** wording after gate green (retain TRAIN/DEVELOPMENT/holdout SEALED / not independent validation / ML-D/E not started)
- Literature audit: original “no ML model” statement remains framed as true **at audit time**; current phase note documents ML-C.1b offline experimental baselines

---

## Non-claims

- Untouched holdout evaluation is **not** completed and not claimed
- Development metrics are **not** independent validation
- No production RuleEngine wiring
- ML-D / ML-E not started
- No commit / no push in this gate session
