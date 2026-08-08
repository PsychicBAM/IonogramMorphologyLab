# ML-C.1b Acceptance Report

**Build Identity:** ML-C.1b  
**Protocol:** `iml-ml-offline-baselines-0.1.0` (unchanged)  
**Branch:** `phase/ml-c1-offline-baselines`  
**Mode:** Offline experimental only  

## Owner screenshot finding (ML-C.1a)

Development Evaluation for Majority Class showed invalid class token `m` alongside
`frequency_spread`, `mixed_spread`, and `range_spread`. Macro F1 displayed raw
Python `None`. Error Analysis listed item IDs but left reference / prediction /
group / date columns blank.

## Root cause of `m`

**Baseline logic bug (not fixture):**  
`MajorityClassBaseline.predict` used `np.full(n, self.majority_class_, dtype=str)`.  
NumPy interprets `dtype=str` as unicode length 1 (`<U1>`), truncating
`mixed_spread` → `m`.  

Confirmed: model artifact stored full `majority_class: "mixed_spread"` while
`predictions_development.jsonl` contained `"prediction": "m"`.

Synthetic fixture labels were already complete canonical tokens
(`mixed_spread`, `frequency_spread`, `range_spread`).

## Fixes

1. **Majority label integrity** — predict/serialize/reload preserve full canonical TRAIN label; never `dtype=str` fill.
2. **Nearest Centroid / Logistic** — predictions and class keys forced to complete string tokens (`dtype=object` / explicit `str`).
3. **Fail-closed label guard** — `label_integrity.validate_evaluation_labels` before metrics; invalid prediction `m` raises `LabelIntegrityError` with EN/RU messages; no trusted completed metrics from invalid labels; malformed tokens never become confusion-matrix axes.
4. **Undefined metric display** — artifacts may store `null`; UI shows `N/A` / `Не определено`; never coerce undefined → `0.0`.
5. **Error Analysis completeness** — UI reads `predictions_development.jsonl` (field-aligned); `error_cases.jsonl` now includes `expert_reference` / `prediction` / group / date / `correct`; missing optionals render `—`.
6. **Historical invalid QA** — completed experiments containing `m` are not rewritten; Verify Integrity surfaces “Prediction artifact contains an invalid morphology label.”

## Tests

Focused: `tests/test_mlc1b_*.py`  
Regression: `tests/test_mlc1*.py`  
Warning audit on `test_mlc1b_*` (no new product warnings beyond pytest-asyncio config noise).

## Validators / hygiene

- `scripts/validate_ml_offline_baselines.py` — extended label / denominator / holdout checks; historical workspace malformations warned, not rewritten  
- `validate_ml_dataset_manifests.py`  
- `validate_ml_dataset_readiness.py`  
- `validate_i18n.py`  
- `validate_docs.py`  
- `check_repository_hygiene.py` → 0  

## Build

- Build Identity: **ML-C.1b**  
- EXE SHA-256: `1BA1E89E7B51C32992D7C3D00B807D4854EE2135DF5F25729CBA6322BDC3C484`  
- Differs from ML-C.1a: `84D3F76200A3BBE7E329CF169DFDE6B1D38EE784133957B51471E71A72BE6530`

## Programmatic smoke (new experiments)

Workspace: `workspaces/MLC1_Offline_Baselines_QA_8a22c20228f2`  
Manifest: `manifest_edd6e7a46b3c`

| Baseline | Experiment | n | Predictions | CM labels | Overall | Macro F1 |
|----------|------------|---|-------------|-----------|---------|----------|
| Majority Class | `mlc_21af3cb4c78e` | 9 | `mixed_spread` only | frequency_spread, mixed_spread, range_spread | 0.0 | null → UI N/A |
| Nearest Centroid | `mlc_d448ea6f8bb4` | 9 | frequency_spread, range_spread | same valid set | 1.0 | 1.0 |

Historical malformed experiments (`mlc_607b3d3f01fa`, `mlc_93a4fbbc9efb`) still contain `m` and were **not** rewritten.  
Holdout: SEALED / UNUSED. Error Analysis fields populated on new runs.

## Packaged owner smoke (still required)

Open the portable EXE against the same QA workspace.  
Do **not** reuse malformed completed experiments as proof.  
Confirm UI: no raw `None`, Error Analysis columns filled, RU↔EN, holdout SEALED.

## Deferred / unchanged

- Full pytest deferred  
- README screenshot gallery not refreshed  
- No commit / no push  
- ML-D / ML-E not started  
- TRAIN-only fit, DEVELOPMENT-only evaluation, holdout firewall, feature extractor, manifest governance, production RuleEngine unchanged  
