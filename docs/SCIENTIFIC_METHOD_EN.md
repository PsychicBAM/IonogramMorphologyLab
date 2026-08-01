# Scientific Method — Ionogram Morphology Lab 1.1.1

This document states how IML separates evidence, interpretation, and expert judgment. It is normative for v1.1.1 user-facing workflows — not a substitute for your institution’s study protocol.

## Pipeline overview

```
import → instrument profile → quality audit → raw render → segmentation
  → interpretable features → source-traceable rules → reference comparison
  → disagreement / abstention → expert decision (separate axis) → reproducible export
```

Each stage produces **reviewable artifacts** with provenance fields. Stages must not be collapsed into a single “diagnosis” score.

## Separate scientific axes

| Axis | Question answered | Must not be confused with |
|------|-------------------|---------------------------|
| Data quality | Is the frame usable? | Morphology label |
| Visible morphology | What pattern is suggested by the image? | Physical mechanism |
| Ambiguity / alternatives | What competing labels remain? | Final classification |
| Interference | Is contamination masking traces? | Instrument fault diagnosis |
| Parameters | What numeric estimates does a method propose? | Calibrated ionospheric product |
| Expert decision | What did a qualified reviewer record? | Automated ground truth |

Solar / dawn–dusk context modifiers for morphology are **disabled in IML-1** by design to avoid implicit diurnal claims from metadata alone.

## Candidate vs validated output

Automatic outputs are **candidates** until expert review and external validation under your protocol:

- Batch analysis proposals
- Rule firings and abstentions
- MATLAB Studio script results
- Model Lab classifier scores

Software statuses such as `source_verified` or `project_approved` describe **documentation and review records inside IML**, not peer-reviewed science.

## Provenance minimum

Exports should retain, where applicable:

- Input file checksum and import audit summary
- Application version **1.1.1**
- Instrument profile ID and verification status
- Rule pack version and rule IDs with thresholds
- Method parameters and abstention counts
- Expert decision codes with rationale timestamps

## Abstention and indeterminate outcomes

**Abstention** (rule or method declines to label) and **Indeterminate** (expert decision) are valid scientific outcomes. They must not be silently converted to default labels in reports.

## Testing vs validation

| Activity | What it demonstrates | What it does not demonstrate |
|----------|----------------------|------------------------------|
| Rule Testing Lab on dev set | Implementation behavior vs labels | Transfer to new stations/epochs |
| Internal pytest | Regression safety | Geophysical truth |
| Synthetic teaching data | UI and code paths | Operational ionospheric forecasting |

## Human-in-the-loop requirement

Expert review (**Accept**, **Change**, **Indeterminate**, **N/A**) is a separate recorded axis. Publications should cite both automatic candidates and expert decisions when reporting morphology tables.

## Related documentation

- [Scientific limitations](SCIENTIFIC_LIMITATIONS_EN.md)
- [Morphology methods](MORPHOLOGY_METHODS_EN.md)
- [Rule testing guide](RULE_TESTING_GUIDE_EN.md)
- [Complete user manual](COMPLETE_USER_MANUAL_EN.md)
