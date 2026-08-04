# Formula Registry Guide (EN) — Phase 4A / 4A.1

Registry file: `knowledge_base/FORMULA_REGISTRY.yaml`

## Classifications

1. `exact_physical_formula`
2. `exact_signal_processing_formula`
3. `observational_definition`
4. `morphology_definition`
5. `instrument_specific_procedure`
6. `project_engineering_heuristic`
7. `unsupported_or_incomplete`

Project heuristics must never be shown in the UI or reports as equations taken directly from literature.

## Summary groups (computed)

The registry `summary` is **generated from item classifications** (not hand-copied). Groups:

- `exact_physical_formulas` (e.g. F001 only)
- `observational_definitions` (e.g. F002 — not counted as an exact physical formula)
- `exact_signal_processing_formulas`
- `instrument_specific_procedures` (includes axis conversions such as HEUR_BIN_TO_MHZ)
- `morphology_definitions`
- `project_engineering_heuristics`
- `unsupported_or_disabled`

Instrument-specific conversions must not be listed as exact formulas.  
`observational_definition` must not map into `exact_physical_formulas`.

## Source location (Phase 4A.1)

Source-supported formulas/definitions require structured `source_location` (at least one of printed_page / pdf_page / section / figure / table / equation) and `expression_kind`:
`exact_quotation` | `translated_quotation` | `close_paraphrase` | `project_interpretation`.

Vague citations such as “operational morphology classes” are rejected by `validate_formula_sources.py`.

## Required fields

Every item includes formula_id, concept, source ID, page/equation (when numeric), original and normalized expressions, units, domain, limitations, implementation paths, parity and validation status.

## Explainability

Open **Raw Numeric Signals → Formula explanations** (Expert/Research). Each item answers: what is computed, from which data, formula, variables, units, source/page, applicability, non-applicability, verification status.
