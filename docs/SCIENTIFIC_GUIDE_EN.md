# Scientific Guide (EN) — Ionogram Morphology Lab 1.1.1

## Scope and status

IML records image-based **candidate** morphology and parameter proposals. It does not establish a physical mechanism, replace expert scaling, or validate a method for operational use. Synthetic data exercises software behavior; it is not scientific-validation evidence.

## Canonical morphology tokens

| Rule token | Serialized | UI meaning |
|---|---|---|
| `none` | `clean` | No visible spread |
| `frequency` | `frequency_spread` | Frequency-spread candidate |
| `range` | `range_spread` | Range / virtual-height spread candidate |
| `mixed` | `mixed_spread` | Mixed only with independent dual-axis evidence |
| `artifact` | `interference_dominated` | Interference-dominated |
| `not_assessable` | `not_assessable` | Quality / processing prevents assessment |

Presence of an E/Es/F1/F2/F trace alone must **not** imply spread. Mixed requires independent frequency **and** range absolute evidence, co-location, and balanced axis thicknesses. Processing errors never become positive morphology.

See the living audit: [Morphology Decision Audit v1.1.1](MORPHOLOGY_DECISION_AUDIT_V1_1_1.md).

## Evidence model

Keep these outputs separate in every review and export:

| Axis | Meaning |
|---|---|
| Data quality | Whether the frame is usable for the requested analysis |
| Morphology | A visible-pattern candidate, not a causal claim |
| Ambiguity | Alternatives and reasons to abstain |
| Interference | Possible contamination or masking |
| Parameters | Method-specific, unit-bearing estimates |
| Expert decision | A separately recorded human assessment |

## Required review practice

1. Confirm the imported source, audit result, and instrument-profile status.
2. Inspect image evidence and alternatives before accepting any proposal.
3. Preserve provenance: source hash, profile, application and rule-pack versions, thresholds, and reviewer rationale.
4. Use **Indeterminate** or abstention when the evidence does not support a defensible candidate.
5. Validate rules and models independently on representative, appropriately labelled material before operational use.

## Validation boundary

Internal tests, Rule Testing Lab results, and synthetic teaching examples demonstrate implementation behavior only. They cannot justify a PASS claim for scientific classification on their own. Packaged-EXE and real-data QA are recorded in [Scientific Classification QA](SCIENTIFIC_CLASSIFICATION_QA.md) and [Product Simplification QA](PRODUCT_SIMPLIFICATION_QA.md).

## Limitations (summary)

- Virtual-height axis is nominal, not true height.
- O/X polarization is not separable on Amp_all archives without polarimetry.
- Interference detection is heuristic.
- Local ridge thickness is image evidence, not a physical Spread-F confirmation.
- Absence of automatic mixed/range on a given day is not proof that those morphologies were absent in nature.

## Related references

- [Morphology methods](MORPHOLOGY_METHODS_EN.md)
- [Parameter estimation](PARAMETER_ESTIMATION_EN.md)
- [Morphology decision audit](MORPHOLOGY_DECISION_AUDIT_V1_1_1.md)
- [Scientific Classification QA](SCIENTIFIC_CLASSIFICATION_QA.md)
- Archived method/limitations prose: [Scientific method](archive/scientific/SCIENTIFIC_METHOD_EN.md), [Scientific limitations](archive/scientific/SCIENTIFIC_LIMITATIONS_EN.md)
