# IML v1.1 Separate Scientific Outputs Audit

**Application version:** 1.1.0

## Axes

| Axis | Storage | UI |
|---|---|---|
| layer | `scientific_axes.layer` / `record.layer` | Results table column |
| morphology | `scientific_axes.morphology` (legacy mirror `candidate_morphology`) | Results table column |
| ambiguity | `scientific_axes.ambiguity` | Results table column |
| quality | `scientific_axes.quality` / `data_quality_status` | Results table column |
| parameters | `scientific_axes.parameter_estimates[]` | Parameters page |

## Forbidden pattern

No `ionogram_type` field is used in application source, exports, or `ScientificFrameResult.to_dict()`.
Legacy `candidate_morphology` remains only as a compatibility mirror of the morphology axis.
