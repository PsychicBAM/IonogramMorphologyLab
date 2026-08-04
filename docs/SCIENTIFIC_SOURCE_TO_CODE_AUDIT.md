# Scientific Source-to-Code Audit (Phase 4A)

This audit records what the approved literature registry **explicitly supports**. No formulas were reconstructed from memory. Phase 4A does **not** change RuleEngine morphology outputs.

## Literature items reviewed

| Source ID | Title (short) | Extracted support | Gaps |
|-----------|---------------|-------------------|------|
| A3L007 | ИПГ Вып. 87 | Virtual vs true height; O/X needs polarimetry | Full Appleton–Hartree not page-verified here |
| A3L018 | Panchenko midlatitude SF | Observational SF; frequency & height/range aspects on **printed p.241 / PDF p.2 §1** | “Mixed” is Article 2 project interpretation (A2_PROTOCOL), not a third A3L018 class on a cited page |
| A3L015 | Calvert equatorial SF | Equatorial background only | Must not transfer to KFU midlatitude without warning |
| A3L006 | SVM/CNN SF taxonomy | Secondary taxonomy reference | Not identical to Article 2 labels |
| CALSTAT | Calibration status | Amp_all shape, ff, minute mapping | Gate2 metrology open |
| GETION | Legacy get_ionogram.m | Historical slice `i*256`, height×2.5 | Development-only quirk notes |
| A2_PROTOCOL | Article 2 candidate | Project morphology protocol | Project heuristic — not literature equations |
| F005/F006 | Appleton–Hartree / plasma frequency | — | **unsupported_or_incomplete** — pages not verified |

## Exact physical formulas encoded (executable)

| ID | Expression | Classification | Implementation |
|----|------------|----------------|----------------|
| F001 | `h' = c·τ_g/2` | exact_physical_formula | Python + MATLAB parity helpers |

## Observational definitions (not exact physical formulas)

| ID | Expression | Classification | Notes |
|----|------------|----------------|-------|
| F002 | `h_true ≠ h'` | observational_definition | Guard only; counted under `observational_definitions` |

## Instrument-specific procedures (not exact physical formulas)

| ID | Expression | Classification | Implementation |
|----|------------|----------------|----------------|
| HEUR_BIN_TO_MHZ | `f = f0 + bin·df` | instrument_specific_procedure | Python + MATLAB |
| HEUR_BIN_TO_NOMINAL_HEIGHT | `h'_nom = bin·2.5 km` | instrument_specific_procedure | Python + MATLAB; guarded by F002 |
| F003 | O/X needs polarimetry | instrument_specific_procedure | documentation guard |

## Morphology definitions recorded (not equations)

- `F004`, `DEF_FREQUENCY_SPREAD`, `DEF_RANGE_SPREAD` — A3L018 printed p.241 / PDF p.2 §1 (`translated_quotation`)
- `DEF_MIXED_SPREAD` — A2_PROTOCOL (`project_interpretation`)

## Project heuristics separated

- `HEUR_IML_TRACE_WIDTH_BINS` — must never be presented as a literature equation

## Feature flag

`analysis.scientific_formula_pipeline_enabled = false` (default). Phase 4A does not enable automatic morphology changes from this registry.
