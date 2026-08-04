# PHASE4C1 Ruleset Rationale (`iml-morph-candidate-rules` 0.1.0)

## Status flags

| Flag | Value |
|---|---|
| provisional | true |
| scientifically_validated | false |
| production_enabled | false |
| candidate_engine_version | iml-morph-candidate-0.1.0 |
| compatible_feature_versions | iml2-0.2.0 |

## Provenance

All numerical thresholds in `config/morphology_candidate_rules_v0_1.json` are **provisional engineering seeds**.

They were **not** tuned against:

- the eight geometry-reviewed frames;
- unreviewed archive frames to make examples “look correct”;
- published accuracy targets.

Where literature-calibrated cut-points are unavailable, the ruleset prefers **abstention** (`indeterminate` / `not_assessable`) over forced classification.

## Decision order

1. Identity and compatibility gates  
2. Required-feature availability (no silent zero substitution)  
3. Frame/data validity  
4. Geometry validity  
5. Trace assessability  
6. Blocking interference / artifact gates  
7. H evidence evaluation  
8. V evidence evaluation  
9. Independence / coexistence evaluation  
10. Temporal evidence adjustment (optional)  
11. Candidate decision  
12. Evidence-strength assignment  
13. Warnings and provenance  

Quality/blocking gates always precede morphology scores.

## Axis contracts (summary)

- **Frequency candidate**: supported H evidence with persistence/coverage; not noise, floor, secondary echo, or branch duplication alone.  
- **Range candidate**: supported V evidence with persistence; never full-height stripes or floor clutter.  
- **Mixed**: independently supported moderate+ H and V **and** coexistence score/fraction; never two weak global scores.  
- **No supported visible spread**: assessable, sufficient geometry, neither axis supported, interference not blocking.  
- **Indeterminate / not assessable**: explicit abstention reasons required.

## Interference

Interference is a **separate axis** (`none|low|moderate|high|blocking`). It may reduce strength or force abstention; it must never increase morphology candidate strength and must never be emitted as a morphology class.

## Temporal

Optional. Missing neighbours are not negative evidence. Temporal context cannot turn `not_assessable` into a morphology label. Consistent neighbours may strengthen moderate evidence only.

## Scientific non-claims

No accuracy, sensitivity, specificity, F1, or agreement is claimed for this ruleset.
