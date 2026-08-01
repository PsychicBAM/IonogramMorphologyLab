# Troubleshooting — 1.1.1

Structured fixes for common Ionogram Morphology Lab issues. If a step references UI labels, English names are shown; Russian labels appear when the interface language is **Русский**.

## Import fails

Confirm the file is a supported **MAT v5/v7** (SciPy) or **v7.3/HDF5** (h5py) archive, readable by your account, and contains an expected array variable.

1. Open **Import Data → Data Audit**.
2. Preserve the **exact warning text** in your study log — do not paraphrase.
3. Do not rewrite a restricted source file in place; use a working copy only under study policy.
4. Verify variable name, shape, and dtype match your instrument documentation.

If audit reports unknown layout, treat compatibility as **unproven** until you validate with your station’s format.

## No frames or wrong orientation

1. Open **Instrument Profile** and confirm frequency/height bins, MHz step, and variable mapping.
2. In **Viewer**, compare the raw frame with the selected transform and navigation direction.
3. Mark provisional metadata explicitly until an expert confirms scaling.

A display correction in the viewer is **not** proof that metadata are scientifically correct.

## Analysis blocked or cache is slow

1. Reduce import scope (fewer files or frames) for first tests.
2. Ensure free disk space for Zarr cache under the project workspace.
3. Use **Build cache** only for stable derived data you intend to reuse.
4. Delete **derived cache** only — never source MAT — when rebuilding.

Collect logs without sensitive paths before requesting support. Home shows blocked steps when cache or profile prerequisites are missing.

## MATLAB backend unavailable

Core workflows do **not** require MATLAB.

1. Open **MATLAB Studio** and read backend status in **Settings → MATLAB**.
2. Verify a licensed local installation or Octave path when execution is required.
3. Use built-in morphology methods or Python-side workflow if backend reports `none` or `no_backend`.

`no_backend` after a run attempt means execution was disabled — it does **not** mean analysis succeeded silently.

## Rule will not run

1. Open **Rule Builder** and check rule ID, target axis, feature registry coverage, units, applicability, and status.
2. Use **Preview generated code** to inspect abstention and exclusion branches.
3. Test in **Rule Testing Lab** on an eligible labelled development set.

A syntactically valid rule may still be scientifically inapplicable to your profile or epoch.

## Expert review or report incomplete

1. Return to **Expert Review** and **Ionogram Parameters**; save decisions with required rationale.
2. Re-export from **Reports** with provenance fields selected.
3. Confirm rule pack version and instrument profile ID appear in export metadata.

Exported HTML/Markdown may contain local paths from your session — review before sharing.

## Performance and memory

| Symptom | Mitigation |
|---------|------------|
| UI freezes during batch | Reduce frame count; lower worker count in Settings |
| Disk fills quickly | Archive old projects; prune derived cache only |
| Slow first open of MAT v7.3 | Expected for large HDF5; build cache once |

## Getting help

1. Note IML version **1.1.1** from About or `project.json`.
2. Attach sanitized logs — redact paths and restricted filenames.
3. Do **not** attach private ionograms or credentials to public issues.
4. See [FAQ](FAQ_EN.md) and [Security reporting](../SECURITY.md).

## Related guides

- [Installation](INSTALLATION_EN.md)
- [Quick start](QUICK_START_EN.md)
- [Rule testing guide](RULE_TESTING_GUIDE_EN.md)
- [MATLAB Studio guide](MATLAB_STUDIO_GUIDE_EN.md)
