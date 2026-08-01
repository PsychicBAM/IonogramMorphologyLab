# Layer Detection Methods

## Separate scientific axes
IML records layer (`E`, `Es`, `F1`, `F2`, and indeterminate values), morphology, ambiguity, and quality separately. A layer candidate is not a morphology category; frequency spread, range spread, interference, and possible O/X are not layer identifications.

## Candidate workflow
1. Audit the frame and profile compatibility.
2. Derive trace and interference diagnostics.
3. Apply source-traceable rules or `matlab_builtin/` candidate methods.
4. Preserve alternatives, contradictions, source pages, and limitations.
5. Export a candidate result for expert review.

The application does not infer a physical formation process from a visible trace. If a trace is not separable, use `F_unspecified`, `multiple_layer`, or `indeterminate` as appropriate instead of forcing a label.

## E and Es
E and Es are layer-axis candidates. A concurrent diffuse or spread-like appearance is stored on the morphology axis. Es subtype wording may only come from `knowledge_base/ES_SUBTYPE_SOURCE_REGISTRY.csv`; the registry must not be expanded with remembered letter lists or unsupported numerical criteria.

## F1 and F2
F1 and F2 candidates require profile-compatible trace evidence. Overlap, insufficient quality, branch structure, or ambiguous separation should remain visible as limitations or ambiguity rather than being silently resolved.

## Parameters
Candidate parameters include a value, unit, estimation method, calibration status, source rule, and limitation. Nominal virtual height is not true height. Treat image-derived values as estimates unless an external measurement protocol supports a stronger statement.

## Scientific Strict
Scientific Strict exposes only status-eligible rules. It does not overcome missing calibration, profile mismatch, unresolved O/X ambiguity, or absent independent validation.
