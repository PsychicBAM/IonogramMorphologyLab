# Built-in MATLAB Ionogram Methods

## Scope
`matlab_builtin/` contains bundled, read-only MATLAB reference methods. They provide reproducible engineering and candidate-detection workflows; they do not establish an ionospheric interpretation, a validated accuracy, or a causal mechanism from an image.

## Layout
- `core/`, `trace_detection/`, and `rendering/` prepare derived inputs and diagnostic displays.
- `layer_detection/`, `es_analysis/`, and `f_layer_analysis/` produce candidate layer evidence.
- `spread_f_analysis/`, `interference/`, and `branch_analysis/` describe candidate morphology and ambiguity evidence.
- `parameters/`, `comparison/`, `temporal_analysis/`, `reports/`, and `tests/` support review and documented development work.
- `manifests/*.iml-matlab.yaml` declare entry points, expected inputs/outputs, parameters, status, and limitations.

## Using a method
Open MATLAB Studio, inspect the method and its manifest, select an isolated workspace, and run it on derived inputs. Record the backend version, input profile, parameters, source hash, output paths, warnings, and error logs. Source MAT files remain read-only.

Layer, morphology, and ambiguity are independent outputs. For example, `iml_detect_f2_candidate.m` can contribute only F2 candidate evidence; `iml_detect_frequency_spread_candidate.m` describes morphology; `iml_detect_possible_ox_pattern.m` contributes ambiguity. Do not merge these into one “ionogram type.”

## Editing
Do not edit files under `matlab_builtin/`. Use MATLAB Studio’s editable-copy action, which writes to `matlab_user_methods/` in a project or user library and retains provenance. A modified copy starts as locally authored/development code and must not inherit source-verified status.

## Scientific Strict
Scientific Strict filters rules and results by their documented status. It does not make a MATLAB routine scientifically validated. Methods without compatible source, profile, domain, or limitation metadata should remain excluded or clearly labelled for development review.

## Validation boundary
Synthetic examples and bundled MATLAB tests verify interfaces and expected control flow only. They are not scientific validation data. Compare against documented, independently labelled material under an appropriate protocol before making any performance claim.
