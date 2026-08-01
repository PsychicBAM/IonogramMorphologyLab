# Complete User Manual — 1.1.1

This manual describes the current desktop UI. Button labels may be localized; English labels are shown below. Treat all automatic results as **reviewable proposals**, not final science.

## Workflow prerequisites

- Work only on files you are authorized to process.
- Use a writable workspace folder outside the install directory.
- Retain source identifiers, instrument profile metadata, and audit warnings in your study log.
- A derived Zarr cache is **not** a source record.

## Ten tutorials

### Tutorial 1 — Create a traceable project

1. On **Home**, select **New Project**, enter a name, choose a workspace folder, and select **Create**.
2. Record the workspace path and project ID in your study log.
3. Do not import research MAT until synthetic teaching files succeed.

### Tutorial 2 — Import and audit a MAT file

1. Open **Import Data**, select **Import MAT file**, choose a permitted file.
2. Inspect **Data Audit** before continuing — preserve exact warning text.
3. Confirm variable name, shape, and time span against instrument documentation.

### Tutorial 3 — Configure an instrument profile

1. Open **Instrument Profile**, run **Profile wizard** or select a bundled profile.
2. Set **verification status** honestly (`provisional` until expert review).
3. Select **Save profile** and confirm warnings were not suppressed.

### Tutorial 4 — Navigate raw frames

1. Open **Viewer**, choose a frame, use **Previous/Next**.
2. Inspect metadata and scaling; optionally select **Build cache** for derived Zarr.
3. Navigate several frames to confirm orientation looks plausible.

### Tutorial 5 — Run batch analysis

1. Open **Batch Analysis**, confirm scope, profile, and rule pack versions.
2. Select **Start** and wait for completion status.
3. Open **Results** — read outputs as candidate proposals on separate axes.

### Tutorial 6 — Review morphology proposals

1. In **Results**, select a row and compare overlays with the raw frame.
2. Open **Expert Review** for frames that matter to your study.
3. Record rationale when overriding automatic candidates.

### Tutorial 7 — Estimate ionogram parameters

1. Open **Ionogram Parameters**, select **Load from last result**.
2. Inspect units, method name, and uncertainty fields.
3. Choose **Accept**, **Reject**, or **Indeterminate**, then **Save expert edits**.

### Tutorial 8 — Build a no-code rule

1. Open **Rule Builder**, select **New rule**, complete wizard pages.
2. Use **Preview generated code** to inspect abstention branches.
3. Select **Save rule** — a new versioned YAML snapshot is written.

### Tutorial 9 — Test a rule against labels

1. Open **Rule Testing Lab**, choose rule version and labelled dataset.
2. Declare split method, set metrics and optional threshold sweep.
3. Select **Run test**, review failures in **Viewer**, export run record.

### Tutorial 10 — Export a reproducible report

1. Open **Reports**, select language and provenance fields to include.
2. Choose **Export** formats (CSV, JSON, HTML, Markdown as needed).
3. Archive report with project manifest and instrument profile version.

## Results and provenance

Read each result with its input checksum, software version **1.1.1**, profile ID, method/rule identifiers, thresholds, timestamps, and expert decision. **Indeterminate** is a valid outcome — not a failure to hide.

## Data protection

The application is local-first, but local storage remains subject to your organization’s access controls. Do not include restricted frames in issue reports, screenshots, or exported examples without redaction.

## Related guides

- [Troubleshooting](TROUBLESHOOTING_EN.md)
- [FAQ](FAQ_EN.md)
- [Parameter estimation](PARAMETER_ESTIMATION_EN.md)
- [Rule testing](RULE_TESTING_GUIDE_EN.md)
- [Scientific limitations](SCIENTIFIC_LIMITATIONS_EN.md)
