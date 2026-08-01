# MATLAB Studio — User Guide (1.1.1)

## Purpose

MATLAB Studio is the **optional** scripting workspace in Ionogram Morphology Lab. It lets researchers maintain, version, run, and review MATLAB or GNU Octave scripts without making the host application depend on a proprietary runtime. It supports reproducible research workflows — not unattended scientific certification.

Core IML features (import, viewer, batch analysis, expert review, reports) work when MATLAB Studio execution is disabled (`none` backend).

## Before you begin

1. Open **MATLAB Studio** from the left navigation.
2. Choose a backend in **Settings → MATLAB**.
3. Supported backend identifiers: `matlab_engine`, `octave`, `external_matlab`, `none`.
4. Detection may report `none` on machines without MATLAB — library, manifests, editing, and packaging remain available; execution is explicitly disabled.

## Script library

Import or create scripts in the project or global library. Each save creates a version record with script hash, timestamp, comment, and application version **1.1.1**.

- Use descriptive names and preserve scientific status in the manifest.
- Imported scripts are **not** verified merely because they execute.
- Treat third-party `.m` files like any unreviewed code.

## Running a script

1. Select a script and inspect its manifest (inputs, outputs, status).
2. Select execution context: current frame, selected frames, or sequence.
3. Enter documented parameters and a timeout.
4. Start the job; review status, log, files, and registered results.

Jobs run in a separate working directory. Inputs copy or serialize to bridge files; source MAT files are hashed before and after execution. Terminal statuses: `ok`, `error`, `timeout`, `cancelled`, `no_backend`. **`no_backend` never means analysis succeeded.**

## Data exchange and outputs

| Artifact | Role |
|----------|------|
| `iml_bridge_inputs.mat` | Matrix payload for script |
| `iml_metadata.json` | Descriptive context and parameters |
| `iml_*` helpers | Register derived matrices, figures, tables in run result |

Do **not** write back to imported MAT — source data are read-only by default.

## Scientific safeguards

MATLAB output is a **candidate** result. Register features, warnings, and provenance including algorithm version and parameters. Do not convert a plot, numeric score, or exit code zero into validated morphology or a physical mechanism claim. Review O/X ambiguity, data quality, profile applicability, and abstention before expert decision.

## UX modes

| Mode | MATLAB Studio visibility |
|------|--------------------------|
| Guided | Deferred — switch to Research/Expert on Home |
| Research | Visible with warnings |
| Expert | Full editor, run log, manifest tabs |

## Troubleshooting

| Issue | Action |
|-------|--------|
| Execution unavailable | Verify backend path; use library without running |
| Timeout | Reduce scope; increase timeout only after script review |
| Invalid manifest | Fix required identifiers and status fields |
| Missing results | Confirm outputs saved via `iml_*` helpers |

Preserve logs and exported provenance when reporting issues — redact local paths.

## Related documentation

- [MATLAB Plugin Developer Guide](MATLAB_PLUGIN_DEVELOPER_GUIDE_EN.md)
- [MATLAB API Reference](MATLAB_API_REFERENCE_EN.md)
- [Plugin architecture](PLUGIN_ARCHITECTURE.md)
- [Troubleshooting](TROUBLESHOOTING_EN.md)
