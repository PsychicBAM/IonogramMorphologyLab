# Feature Pipeline V2 Guide (EN)

**Version:** `iml2-0.2.0`  
**Flag:** `analysis.scientific_feature_pipeline_v2_enabled` (default **false**)  
**Label:** Experimental features — not used by the current classification

Do not mix `iml2-0.1.0` and `iml2-0.2.0` outputs without displaying their versions explicitly.
Prior 0.1.0 evidence remains under `docs/_phase4b1_*`; current evidence under `docs/_phase4b3_iml2-0.2.0_*`.

## Separation of concerns

| Layer | Meaning in V2 |
| --- | --- |
| **Measurement** | Numeric quantities, masks, centerlines, uncertainty |
| **Interpretation** | Candidate geometric readings (branches, O/X ambiguity *possibility*) |
| **Classification** | **Not performed** by V2 in Phase 4B |
| **Validation** | Synthetic geometry tests + automatic real-frame shadow audit; owner review pending. |

V2 does **not** emit `frequency_spread`, `range_spread`, or `mixed_spread`.  
V2 does **not** change RuleEngine thresholds or morphology decisions.

## Primary data path

1. Numeric frame from `extract_frame_consistent`
2. Signal contract ID (`kfu_amp_all_v1` / Amp_all)
3. Optional frequency / nominal height axes
4. Source MAT identity (SHA), profile, processing / feature version

Do not analyse a saved PNG when the numeric frame is available.  
Unresolved variables (`Phs_all`, `Date_Time1`, `AmEsP`, `A_map_F`, `H_map_F`) are excluded.

## Representations

1. **Raw** — unchanged MAT values (`status: scientific`)
2. **Derived diagnostic** — normalization / background score (`status: diagnostic`)
3. **Masks** — candidate/accepted trace, interference, background, uncertain, excluded

Derived frames are never serialized as raw.

## Modules

- Quality gates → `assessable` / `degraded` / `interference_limited` / `not_assessable`
- Trace extraction (multi-stage, explainable)
- Local width estimators (FWHM, percentile, second moment, support)
- Interference axis (separate levels including `prevents_assessment`)
- Branch / alternative structure (candidate interpretations)
- Temporal neighbors (optional; abstain if unavailable)

## Expert UI

**Feature Diagnostics** page: synchronized layers, opacity, fit/100% zoom with aspect ratio preserved, feature explanations, diagnostic package export.

## Next phase

Phase 4C will decide which *validated* measurements may later activate classification rules.
