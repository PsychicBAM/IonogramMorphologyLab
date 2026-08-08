# ML-C.1 Acceptance Report

**Build Identity:** ML-C.1  
**Protocol:** `iml-ml-offline-baselines-0.1.0`  
**Mode:** Offline experimental only  
**Date:** 2026-08-08

## Purpose

ML-C.1 establishes a controlled offline experimental baseline harness above a **frozen** ML-B dataset manifest.

It answers:

- Can a simple candidate-independent single-frame baseline be fit reproducibly on TRAIN?
- What descriptive agreement does it obtain against selected expert reference labels on DEVELOPMENT?
- Which classes are confused and which development items are errors?
- Are results reproducible under the same manifest, feature extractor, baseline, and seed?
- Is the untouched holdout still sealed and completely unused?

It does **not** answer scientific validation, untouched generalization, production readiness, temporal modeling, or CNN/LSTM deployment.

## Supported surfaces

| Surface | Status |
|---------|--------|
| Task A — Spread-F morphology classification | Supported |
| Other ML-B task contracts | Visible as unsupported with readable reason |
| Feature extractor `iml-single-frame-pool16-0.1.0` | Supported (256 features) |
| Majority Class `iml-majority-class-baseline-0.1.0` | Supported |
| Nearest Centroid `iml-nearest-centroid-pool16-0.1.0` | Supported |
| Logistic Regression `iml-logistic-regression-pool16-0.1.0` | Supported (scikit-learn already declared) |
| Holdout evaluation / unlock | Forbidden |
| Production RuleEngine wiring | Not started |
| ML-D / ML-E | Not started |

## Holdout firewall

Normal ML-C execution:

- never opens `holdout_reference_labels.jsonl`;
- never loads holdout frames for prediction;
- never writes holdout predictions or metrics;
- never uses holdout for normalization, balancing, or tuning;
- exposes only approved aggregate holdout metadata (counts, hashes, sealed state).

Attempted item-level holdout access fails closed as a protocol violation.

## Feature contract

- Candidate-independent single-frame pooled image 16×16 → 256 numeric features
- Robust per-frame intensity normalization; TRAIN-only feature standardization where required
- Forbidden predictors: candidate outputs, identity/leakage fields (project/item/source/date/role/reviewer/manifest IDs, etc.)
- No temporal windows

## Metrics wording

Development metrics are **development-set agreement against selected expert reference labels**.  
They are **not** independent validation and **not** untouched-holdout performance.

## UI readability

Offline ML Baselines page provides:

- collapsible / hideable panels;
- View menu (show/hide secondary panels);
- More ▾ overflow for secondary actions;
- compact contextual primary actions;
- resizable splitter workspace;
- table column visibility controls;
- Technical Details collapsed by default;
- always-visible holdout SEALED banner and development-metrics caveat.

## Verification (implementation gate)

- Focused `tests/test_mlc1_*` suite: **21 passed**
- Warning audit on focused suite: no ML-C.1-introduced product warnings (pre-existing pytest-asyncio config notice only)
- Validators including `validate_ml_offline_baselines.py`: all PASS / OK
- Repository hygiene: **0**
- Portable EXE rebuilt; SHA-256 differs from ML-B.1d  
  New EXE SHA-256: `2CE8C295A79DC601A8F743A53DC879D23641D97F8B4CB2DA4001F516A561DA7D`
- Full pytest deferred until after owner visual QA

## Non-goals preserved

- No scientific validation claims
- No holdout unlock path
- No production RuleEngine wiring
- ML-D and ML-E not started
- No commit/push in this implementation phase
