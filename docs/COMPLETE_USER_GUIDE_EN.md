# Ionogram Morphology Lab 1.1.0 — Complete User Guide

## What the application does
Ionogram Morphology Lab / Лаборатория морфологии ионограмм organizes MAT-based ionogram work: import, audit, cache, rendering, interpretable features, source-traceable rules, reference comparison, candidate results, expert decisions, and export. It does not establish morphology, mechanism, or accuracy by itself.

## First launch and language
On first launch choose the interface language. Later change it only through **Settings → General → Interface language**. There are intentionally no top-bar EN/RU language buttons. Restart or refresh the relevant view if prompted after changing language.

## Project workflow
1. Create a workspace project.
2. Import a MAT file or folder and inspect variables/profile.
3. Run a quality audit; resolve unreadable, invalid-shape, or insufficient-metadata states.
4. Build the derived cache and open real frames in Viewer.
5. Select frames, run features/rules, inspect disagreements and abstentions.
6. Record a separate expert decision if appropriate.
7. Export CSV, JSON, HTML, or Markdown with provenance.

Imported source MAT files are read-only by default. Cache and reports are derived data; source SHA supports traceability.

## Analysis modes
Choose **Settings → Analysis → Mode**:
- `fast_preview`: rapid browsing; not a final scientific basis.
- `standard`: balanced operational settings.
- `scientific_strict`: recommended default; retains quality, provenance, disagreement, and abstention safeguards.
- `custom`: explicit user-selected options; document deviations in reports.

## Protected Scientific Study mode
**Protected Scientific Study** is optional and off by default. When enabled and configured it can apply path protections to specified study material. It is not a substitute for access control, ethics approval, or a data-governance plan. Do not enable it casually without confirming its configured fragments and expected scope.

## Results and limitations
Results are candidate morphologies. `abstain`, `indeterminate`, or a null confidence are informative, not failures. A null confidence means no calibrated probability is available. Do not infer O/X identity from visual branching alone. User profiles and imported methods require their own validation.

## Extensions
MATLAB Studio provides isolated scripts and plugins; Model Lab provides development models. Both must preserve provenance and neither replaces expert review. See [MATLAB Studio](MATLAB_STUDIO_GUIDE_EN.md), [Model Lab](MODEL_LAB_GUIDE_EN.md), and the [scientific method](SCIENTIFIC_METHOD_EN.md).
