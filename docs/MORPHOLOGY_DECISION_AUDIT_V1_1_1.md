# Morphology Decision Audit — v1.1.1

**Status:** living scientific QA document for the product-simplification phase  
**Software version:** 1.1.1  
**Primary MAT (approved non-secret local archive):** `Am_all_2014-09-25.mat`  
**Instrument profile:** `kfu_cyclone_2013_2014.yaml`  
**Decision path audited:** feature extraction → RuleEngine (Python rule pack `RULE_PACK_IML1`) → `normalize_morphology` serialization → UI presenters  

MATLAB/ML ensemble candidates are **not** merged into the production batch path in v1.1.1; this audit therefore focuses on the RuleEngine path that users actually see.

---

## Canonical non-spread token

| Layer | Token | Localized meaning (EN) | Localized meaning (RU) |
|-------|-------|------------------------|------------------------|
| Rule engine | `none` | No visible spread evidence | Явное рассеяние не обнаружено |
| Serialized / export | `clean` | Clean / no visible spread | Чистая трасса / без явного рассеяния |
| UI display | translated label | “No visible spread” | «Явное рассеяние не обнаружено» |

**Do not** treat presence of an E/Es/F1/F2/F trace as automatic spread.  
**Do not** emit `mixed_spread` unless independent frequency **and** range absolute evidence co-locate with balanced axis thicknesses.

---

## Root cause of prior “always mixed_spread” behaviour

Before this phase, many visible traces became `mixed_spread` because:

1. **Global row/column span widths** treated sloping thin ridges as broad on both axes.
2. **R003** could activate from `mixed_width_score` / Boolean `mixed_coverage` without true dual-axis absolute evidence.
3. **R004 (clean/none)** required near-empty frames (`trace_pixel_fraction ≤ 0.02`), so ordinary clean traces could not reach a non-spread category.
4. **NaN** threshold comparisons could incorrectly satisfy rules.

### Corrective logic (v1.1.1)

- Primary evidence = **local ridge thickness** (EDT-capped axis runs), not global spans.
- Gates: `frequency_evidence_passed` / `range_evidence_passed` (axis dominance) and `frequency_evidence_absolute` / `range_evidence_absolute` (absolute thickening).
- **Mixed** requires: both absolute axes + `colocated_spread_fraction ≥ 0.20` + balanced axis ratio (`≤ 1.85`) + `min(med_h, med_v) ≥ 8`.
- Unbalanced dual-axis thickening → `none`/`clean` with status `uncertain` (`dual_axis_thickening_unbalanced_not_mixed`), not mixed or forced single-axis spread.
- Vertical full-height stripes block spread only with **co-evidence** (`full_height_stripe_count ≥ 3` **and** `interference_dominance ≥ 0.25`), or stronger stripe/dominance thresholds.
- Processing / quality failures → `not_assessable` only (never a positive morphology).
- Feature vector version: `iml1-0.2.0`.

---

## Real-data survey (Am_all_2014-09-25)

Sampling every 20th frame (72 frames):

| Morphology (serialized) | Count |
|------------------------|------:|
| `clean` | 49 |
| `interference_dominated` | 16 |
| `frequency_spread` | 7 |
| `range_spread` | 0 |
| `mixed_spread` | 0 |

**Implication:** On this day, after the fix, the dominant assessable non-interference outcome is **clean**, not mixed.  
No automatic `range_spread` / `mixed_spread` appeared in the subsample. Positive range/mixed claims for this archive day therefore require **expert confirmation** on additional frames or other approved labelled material; atlas cases REF003/REF001/REF006 remain the definitional references.

Denser sampling (every 5th frame) likewise found **no** automatic `range_spread` / `mixed_spread` and **no** `possible_ox_compatibility ≥ 0.5`.

---

## Audited frames

### A. Interference-dominated — frame 1 (~00:00)

| Field | Value |
|-------|-------|
| Source | `Am_all_2014-09-25.mat` |
| Frame | 1 |
| Interpreted time | 00:00 |
| Visible layer candidate | Trace present (`trace_pixel_fraction ≈ 0.048`) |
| Morphology | `interference_dominated` (rule `artifact`) |
| Quality | `valid` |
| Ambiguity / disagreement | `artifact_vs_real_trace`, `frequency_vs_vertical_interference`, `mixed_vs_interference` |
| Interference | `interference_dominance ≈ 0.403`; stripe density ≈ 0.035 |
| Features (key) | `fe_passed=1`, `re_passed=0`, `med_h≈14.1`, `med_v≈6.2` |
| Rules fired | R005 |
| Rules rejected / blocked | Frequency candidate blocked by interference co-evidence |
| Thresholds | inter ≥ 0.55 **or** stripe dens. ≥ 0.2 **or** (full-height ≥ 3 **and** inter ≥ 0.25) |
| Final decision | Artifact / interference-dominated |
| Reason | Stripe + dominance co-evidence; spread labels suppressed |
| Limitations | Heuristic interference detector; not a physical RFI diagnosis |
| Expert expectation | Do not call frequency/range/mixed when stripes dominate |

### B. Clean visible trace (required negative control) — frame 421 (~07:00)

| Field | Value |
|-------|-------|
| Source | `Am_all_2014-09-25.mat` |
| Frame | 421 |
| Interpreted time | 07:00 |
| Visible layer candidate | Clear F-region-like ridge (`trace_pixel_fraction ≈ 0.067`) |
| Morphology | **`clean`** (rule `none`) |
| Quality | `valid` |
| Ambiguity | `unbalanced_dual_axis_thickening`, `mixed_requires_both_balanced_axes` |
| Interference | `interference_dominance ≈ 0.157` (below co-evidence gate) |
| Features (key) | `fe_abs=1`, `re_abs=1`, `fe_passed=1`, `re_passed=0`, `med_h≈22.4`, `med_v≈10.1`, colocated ≈ 0.75 |
| Rules fired | R004 (supporting clean) |
| Rules rejected | R003 mixed discarded (axis ratio ≈ 2.22 > 1.85); single-axis spread not forced |
| Thresholds | mixed needs balanced ≤ 1.85 and min width ≥ 8; here ratio fails |
| Final decision | No visible spread (`clean`) with **uncertain** confidence |
| Reason | Dual-axis thickening present but **unbalanced** — insufficient for mixed; not treated as automatic frequency spread |
| Limitations | Local thickness is image evidence only; sloping geometry can still inflate absolute gates |
| Expert expectation | **Must not** be labelled mixed spread; clean / no_visible_spread is appropriate unless an expert asserts spread |

**Old vs new (f0421):** previously tended toward `mixed_spread` under global-span / loose R003 logic → now `clean` (uncertain).

### C. Clean visible trace — frame 600

| Field | Value |
|-------|-------|
| Frame / time | 600 / interpreted mapping via project time model |
| Morphology | `clean` |
| Rules | R004 |
| Notes | Same unbalanced-or-no-dominance pattern as other daytime clean frames; confirms clean is reachable on real data |

### D. Frequency-spread candidate — frame 800

| Field | Value |
|-------|-------|
| Source | `Am_all_2014-09-25.mat` |
| Frame | 800 |
| Morphology | `frequency_spread` |
| Quality | `valid` |
| Features | `fe_passed=1`, `re_passed=0`, `fe_abs=1`, `re_abs=0`, `med_h≈14.1`, `med_v≈7.4`, inter ≈ 0.18 |
| Rules fired | R001 |
| Final decision | Frequency-spread **candidate** |
| Reason | Absolute + dominant horizontal local thickness without range dominance |
| Limitations | Candidate only; not confirmed physical Spread-F; expert review still required |
| Expert expectation | Acceptable automatic **proposal** when frequency broadening is visually plausible; still not proof |
| Atlas definitional link | REF002 (Panchenko et al. 2018, frequency aspect) — metadata only |

### E. Near-empty / low-echo (proxy)

This MAT day does not contain true all-zero frames in sparse sampling (typical `trace_pixel_fraction` ~0.05–0.07).  
**Implementation empty control** (synthetic `all_zero` / quality `all_zero`):

| Field | Value |
|-------|-------|
| Source | synthetic / quality gate |
| Morphology | `not_assessable` when `quality_status=all_zero`; else `clean` for numeric zeros with `valid` quality |
| Rules | quality short-circuit or R004 |
| Expert expectation | Indeterminate / not assessable — never mixed |

Documented limitation: a dedicated empty-echo real frame from this file was not isolated in the audit subsample; quality-gate behaviour is covered by unit tests.

### F. Range-spread — reachability + definitional reference

| Field | Value |
|-------|-------|
| Real MAT subsample | **No** automatic `range_spread` on `Am_all_2014-09-25` (every 5th/20th frame) |
| Implementation reachability | Synthetic `vertically_diffuse` → `range_spread` via R002 (`med_h≈6.9`, `med_v≈14.6`, `re_passed=1`) |
| Definitional source | Atlas **REF003** (Panchenko et al. 2018, range-diffuse wording) — metadata only; image unavailable in default install |
| Expert expectation | Range may be proposed only with vertical local thickening **not** explained by stripes |
| Limitation | Positive real-data range example for this day is **not** claimed here without expert labelling |

### G. Mixed-spread — reachability + definitional reference

| Field | Value |
|-------|-------|
| Real MAT subsample | **No** automatic `mixed_spread` after the fix (desired: stop false mixed) |
| Implementation reachability | Synthetic `mixed_diffuse` compact blob → `mixed_spread` via R003 (`med_h=med_v=50`, colocated=1) |
| Definitional sources | Atlas **REF001** / **REF006** (mixed / MSF taxonomy) — metadata only |
| Gates required | both absolute axes + colocated ≥ 0.20 + balanced ratio + min width ≥ 8 + no interference block |
| Expert expectation | Mixed only when **both** axes have independent documented evidence |
| Limitation | No expert-confirmed mixed frame from this MAT is asserted in this audit |

### H. Ambiguous branches / O–X proxy

| Field | Value |
|-------|-------|
| Real MAT subsample | No frame with `possible_ox_compatibility ≥ 0.5` in every-5th scan |
| Implementation | Synthetic `clean_double_branch` → `clean` (R004); R006 abstain when ox≥0.5 and ≥2 branches |
| Definitional source | Atlas **REF007** (O/X / virtual-height guidance) |
| Expert expectation | Separated branches must not auto-become spread |

---

## Threshold summary (active development calibration)

| Gate | Typical value | Role |
|------|---------------|------|
| `horiz_thr` / `vert_thr` | 6.0 | Local thickness absolute floor |
| `mixed_thr` | 8.0 | Stricter dual-axis absolute |
| Colocated fraction | ≥ 0.20 | Mixed co-location |
| Axis balance ratio | ≤ 1.85 | Mixed balance |
| Min axis for mixed | ≥ 8.0 | Substantial dual evidence |
| Interference dominance | ≥ 0.55 | Strong artifact |
| Stripe density | ≥ 0.20 | Artifact |
| Full-height + dominance | ≥ 3 and ≥ 0.25 | Stripe co-evidence |

Origins are recorded per rule in `knowledge_base/RULE_PACK_IML1.csv` (`development_calibration` / `derived_from_verified_definition` / `engineering_default`).

---

## Scientific limitations (do not over-claim)

1. Automatic labels are **candidates**, not confirmed physical Spread-F.
2. Virtual-height axis is **nominal**; range spread is image-axis language.
3. Interference heuristics can over- or under-call early-night frames (e.g. f001/f050).
4. Absence of automatic mixed/range on this day is **not** proof that the ionosphere lacked those morphologies.
5. Atlas figures are mostly unavailable in the default install (copyright); citations are metadata-first.
6. Confidence `uncertain` on clean dual-axis-unbalanced frames correctly reflects calibration limits.

---

## Test anchors

- `tests/test_morphology_classification_correctness.py` — clean ≠ mixed; NaN/missing ≠ positive; mixed needs both axes; interference ≠ range; failure ≠ positive morphology; clean reachable; rule trace present.
- Diagnostic scripts (local, not packaged): `workspaces/_run_morph_audit.py`, `workspaces/_morph_diag.py`.

---

## Verdict

| Requirement | Status |
|-------------|--------|
| Visible trace ≠ automatic mixed | **PASS** on f0421 and survey majority → `clean` |
| Clean / no_visible_spread reachable | **PASS** (`clean` / rule `none`) |
| Mixed requires both components | **PASS** (engine + tests; no false mixed in day survey) |
| Frequency without forcing mixed | **PASS** (f0800 candidate) |
| Interference ≠ range | **PASS** (synthetic + R005 path) |
| Real expert-labelled range/mixed on this MAT | **NOT AVAILABLE** in current archive labels — documented as limitation |
| Processing error → positive morphology | **PASS** (quality short-circuit) |
