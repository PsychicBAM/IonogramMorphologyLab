# Quick Start — 1.1.1

This guide walks through a **first successful session** with Ionogram Morphology Lab (IML). It assumes a writable workspace and data you are authorized to process.

> **Before research data:** use [`synthetic_data/`](../synthetic_data/) teaching files. They exercise the interface and pipeline; they do **not** validate a scientific conclusion or prove compatibility with your station’s MAT layout.

## Prerequisites

- IML **1.1.1** installed (portable release or `pip install -e ".[dev]"` from source).
- A dedicated project folder on disk with free space for derived cache (Zarr) and reports.
- Optional: read [Installation](INSTALLATION_EN.md) for platform-specific notes.

## Step 1 — Language and first launch

1. Start the application (`IonogramMorphologyLab` executable or `python -m ionogram_morphology_lab.app.main`).
2. On the first-launch dialog, choose **English** or **Русский**.
3. To change later: **Settings → General → Interface language**.

## Step 2 — Create a project (Home)

1. Open the **Home** page (default landing after launch).
2. Select **New Project**.
3. Enter a project name and choose a **workspace folder** (writable, outside the install directory).
4. Review the **recommended workflow** strip — green/blue/grey steps show progress.
5. Choose a **UX mode** if helpful:
   - **Guided** — minimal advanced surfaces;
   - **Research** — analysis and comparison tools visible;
   - **Expert** — full menus including Rule Builder and Model Lab.
6. Press **Continue recommended step** to jump to the next incomplete action.

![Home dashboard with workflow steps](../assets/screenshots/home_en.png)

*Alt: Home dashboard with recommended workflow steps and UX mode selector.*

## Step 3 — Import MAT data

1. Navigate to **Import Data** (or follow Home’s next step).
2. Choose **Import MAT file** (single file) or **Import Folder** (batch of `.mat` files).
3. Select a file from `synthetic_data/` for your first run.
4. Open **Data Audit** and confirm:
   - variable name and array shape;
   - frame count and time span (if present);
   - frequency axis orientation (compare with your instrument documentation).
5. If audit warnings appear, resolve or document them before batch analysis — do not assume silent correction.

![Import Data with Data Audit](../assets/screenshots/data_audit_en.png)

*Alt: Import Data page with Data Audit summary panel.*

## Step 4 — Instrument profile

1. Open **Instrument Profile**.
2. Select a bundled profile that matches your teaching file, **or** run the profile wizard for a new station.
3. Set **verification status** honestly:
   - use *provisional* or *user-defined-unverified* until an expert confirms metadata;
   - do not mark *verified* without review records.
4. Save the profile to the project.

Frequency bins, height bins, and MHz step must be consistent with the imported array — incorrect profiles produce misleading morphology proposals.

## Step 5 — Viewer and derived cache

1. Open **Viewer**.
2. Select a frame index or timestamp.
3. Inspect the raw ionogram image and side metadata.
4. If prompted, select **Build cache** to create the **derived Zarr cache** (chunked, read-optimized). This does **not** modify the source MAT file.
5. Navigate a few frames to confirm orientation and scaling look plausible.

Skip cache build only when the UI allows direct reads — otherwise later batch steps may be blocked (Home will show a warning state).

## Step 6 — Batch analysis

1. Open **Batch Analysis**.
2. Confirm scope (frames, rule pack version, method selections).
3. Select **Start** and monitor progress.
4. Open **Results** when complete.

Interpret results as **candidate proposals**:

| Column / concept | Meaning |
|------------------|---------|
| Data quality | Whether the frame is usable |
| Candidate morphology | Image-evidence label — not confirmed physics |
| Alternatives / flags | Disagreement or ambiguity markers |
| Auto status | Pipeline confidence / abstention |

## Step 7 — Expert review

1. Open **Expert Review** for frames you care about.
2. For each frame, choose one of:
   - **Accept** — agree with candidate;
   - **Change** — override category (document reason);
   - **Indeterminate** — evidence insufficient;
   - **N/A** — not applicable for this study.
3. Enter a **rationale** (required for overrides).
4. Select **Save expert edits** — decisions are stored in the project audit trail.

Expert review is what makes outputs defensible in a study protocol — auto proposals alone are not sufficient.

## Step 8 — Export reports

1. Open **Reports**.
2. Choose language (**EN** / **RU**) and formats (CSV, JSON, HTML, Markdown as needed).
3. Select **Export** to the project `exports/` area.
4. Archive alongside:
   - `project.json` and manifest;
   - instrument profile version;
   - rule pack version IDs recorded in run metadata.

Review exported HTML/Markdown before publication — they may contain local paths from your session.

## Safe working habits

| Do | Avoid |
|----|-------|
| Keep source MAT **read-only** | Overwriting originals in place |
| Start with synthetic teaching data | Importing restricted/blinded records without governance approval |
| Record provisional metadata explicitly | Marking profiles “verified” without review |
| Preserve provenance with exports | Sharing reports without redacting local paths |
| Read [Scientific limitations](SCIENTIFIC_LIMITATIONS_EN.md) | Treating candidate morphology as physical mechanism |

## Next steps

| Goal | Document |
|------|----------|
| Full UI tour | [Complete user manual](COMPLETE_USER_MANUAL_EN.md) |
| Custom rules | [Custom Rule Builder](CUSTOM_RULE_BUILDER_EN.md) |
| Test a rule pack | [Rule testing guide](RULE_TESTING_GUIDE_EN.md) |
| MATLAB scripts | [Plugin architecture](PLUGIN_ARCHITECTURE.md) |
| Problems | [Troubleshooting](TROUBLESHOOTING_EN.md) · [FAQ](FAQ_EN.md) |

Return to **Home** anytime — the dashboard recalculates the next recommended step from project state.
