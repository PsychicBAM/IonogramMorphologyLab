# PHASE 4C.1 Acceptance Report

**Phase:** Explainable Shadow Morphology Candidate Engine, Abstention Contract, Evidence Ledger, Expert Review Workflow  
**Geometry feature version:** `iml2-0.2.0` (unchanged)  
**Candidate engine version:** `iml-morph-candidate-0.1.0`  
**Ruleset:** `iml-morph-candidate-rules` `0.1.0`  
**Mode:** shadow-only · provisional · not scientifically validated · production_enabled=false  
**Date:** 2026-08-03  

## Verdict

Phase 4C.1 delivers a provisional, explainable morphology **candidate** engine that consumes Feature Pipeline V2 results only, keeps interference as a separate axis, abstains when evidence is insufficient, stores a full evidence ledger, and provides a separate morphology review workflow. Production `RuleEngine` is untouched. No scientific classification validation is claimed.

## Files changed (principal)

### New
- `src/ionogram_morphology_lab/morphology_candidate/` — engine, types, from_v2, rules, cache, reviews, labels, fixtures, export
- `config/morphology_candidate_rules_v0_1.json`
- `scripts/validate_morphology_candidate_shadow.py`
- `tests/test_phase4c1_morphology_candidate.py`
- `docs/PHASE4C1_FEATURE_INPUT_AUDIT.md`
- `docs/PHASE4C1_RULESET_RATIONALE.md`
- `docs/PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md`
- `docs/PHASE4C1_ACCEPTANCE_REPORT.md`

### Modified
- `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` — active provisional morphology panel, sequence columns/filters, morph cache
- `tests/test_phase4b2f_performance_and_identity.py` — Future 4C panel expectations updated for 4C.1

### Explicitly unchanged
- `src/ionogram_morphology_lab/rules/engine.py` (no import/call of candidate engine)
- V2 geometry algorithm / registry scientific thresholds
- Geometry review storage path and schema

## Feature inputs used

Primary rule inputs (see audit for full table):

- Quality/trace: `v2_quality_status`, `v2_trace_pixel_fraction`, `v2_accepted_support_above_floor_fraction`
- H: `v2_horizontal_width_elevated_fraction`, contiguous length, median width, applicable fraction
- V: `v2_vertical_width_elevated_fraction`, contiguous length, median width, applicable fraction
- Mixed: `v2_coexistence_score`, `v2_coexistence_fraction`
- Interference/artifacts: `v2_interference_level`, floor/stripe burdens, oversegmentation, multiple-reflection flag

## Feature inputs rejected / deferred

- Single-extremum widths (`v2_local_*_width_max`) as sole evidence
- Encoding interference level as a morphology class
- Using geometry reviews as morphology ground truth
- Temporal V2 scalars alone (optional `TemporalContext` object used instead)
- Fake probabilities / calibrated confidence

## Provisional thresholds and provenance

All thresholds live in `config/morphology_candidate_rules_v0_1.json` with named, unit-aware, documented entries marked `provisional_engineering_seed`.  
**Not tuned** on the eight geometry reviews or unreviewed frames for cosmetic correctness. Prefer abstention when evidence is weak.

## Decision order

1. Identity/compatibility → 2. Required features → 3–5. Validity/geometry/trace → 6. Blocking interference → 7–8. H/V evidence → 9. Coexistence → 10. Temporal → 11–13. Decision, strength, warnings/provenance.

## Abstention contract

- `not_assessable` / `indeterminate` set `abstained=true` with explicit `abstention_reasons`.
- No valid trace → never frequency/range/mixed.
- Missing required features → not assessable (no silent zeros).
- Blocking interference / severe oversegmentation → abstention.

## Interference contract

Separate object: `none|low|moderate|high|blocking` plus category flags. May reduce evidence or force abstention; never increases morphology strength; never emitted as frequency/range/mixed.

## Mixed independence rule

Requires independently supported moderate+ H and V **and** coexistence score/fraction above provisional minima. Unrelated H/V regions → indeterminate, not mixed.

## Temporal context behaviour

Optional. Missing neighbours are not negative. Cannot upgrade `not_assessable`. May strengthen moderate evidence or force indeterminate on contradiction. Default single-frame mode works without temporal context.

## Evidence-ledger example (structure)

Each entry records `rule_id`, `feature_id`, measured value/unit/validity, threshold, comparison, support direction, ordinal strength, adjustments, RU/EN human explanation, technical explanation. Final decision is reproducible from input + ruleset + ledger.

## Candidate cache identity

Separate from V2 cache under `{cache_root}/morphology_candidates/`. Key includes source SHA, frame, profile, signal contract, V2 feature version, diagnostics cache ID, candidate engine version, ruleset version/hash, temporal signature. Ruleset change invalidates candidate only.

## Review storage

`<project>/feature_diagnostics/morphology_reviews/`  
`review_kind=morphology_candidate_review`, `provisional_expert_review=true`, `confirmed_ground_truth=false` by default. Geometry reviews are never overwritten.

## Synthetic test matrix

20 scenarios covered via fixtures + tests (H-only, V-only, mixed, clean no-spread, no-trace, missing feature, vertical interference, floor, secondary echo, oversegmentation, unrelated H/V, weak boundary, blocking interference, temporal missing/consistent/contradictory, cache invalidation, identity mismatch, deterministic hash, input immutability).

## Test counts

- Full pytest: **395 passed**
- Focused 4C.1: **24 passed** (+ updated Future-4C panel test)

## Validator results

| Validator | Result |
|---|---|
| Feature Registry V2 | OK registry=93 |
| Synthetic geometry V2 | OK 17/17 |
| Feature shadow mode | OK |
| Morphology candidate shadow | OK |
| i18n | OK |
| docs | OK |

## Performance measurements (dev smoke)

Eight-frame shadow audit candidate evaluation: ~2–8 ms per frame on cached V2 `features.json` (well below 100 ms target). Engine does not reopen MAT or rerun V2.

## Production-isolation proof

- AST/import scan: `rules/engine.py` does not import `morphology_candidate`
- Validator `scripts/validate_morphology_candidate_shadow.py` enforces isolation
- Results carry `shadow_mode=true`, `scientifically_validated=false`, `production_applied=false`

## Packaged EXE

| Field | Value |
|---|---|
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| SHA-256 | `D50A5770695F35247D6177EC49E317A9E962B64828E50642CA1C8DB3F6D788A0` |

### Owner manual QA checklist (packaged)

1. Open an existing V2-cached frame  
2. Calculate morphology candidate  
3. Open evidence ledger  
4. Verify RU/EN explanation + shadow disclaimer  
5. Review and save a morphology candidate review  
6. Switch frame → old candidate clears  
7. Return → load candidate cache  
8. Short 05:00–07:00 / 10-minute sequence  
9. Filter indeterminate / not assessable / high interference  
10. Switch language  
11. Switch pages during sequence  
12. Cancel  
13. Confirm no MAT reopen regression  
14. Confirm production analysis results unchanged  

Do not claim scientific accuracy from this QA.

## Eight-frame smoke audit

See `docs/PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md`.  
Several geometry-acceptable / sparse / oversegmented frames are `not_assessable` or `indeterminate` — expected and **not** a contradiction with geometry review. **No “8/8 correct” claim.**

## Scientific non-claims

- No scientific classification validation claimed  
- No accuracy / sensitivity / specificity / F1 claimed  
- Eight geometry reviews are **not** morphology labels  
- Rules and thresholds are provisional  
- V2 remains shadow-only  
- Candidate engine remains shadow-only  
- Production RuleEngine is unchanged  
- Expert morphology reviews are still required  

## Remaining blockers / next work

- Owner packaged EXE manual QA (checklist above)  
- Broader expert morphology review corpus before any validation metrics  
- Optional: tighten coexistence spatial identity if additional registry fields become available  
- Do **not** enable production wiring  

## Git

- **No commit**  
- **No push**  
