# Ionogram Morphology Lab

[English](README.md) | [Русский](README_RU.md) · **Release 1.1.1** · **Build Identity: ML-B.1d**

Ionogram Morphology Lab (IML) is a bilingual (EN/RU) desktop research application for **source-traceable ionogram morphology analysis**, expert review campaigns, disagreement analysis, dataset readiness audits, leakage-safe dataset manifests, rule testing, and report export. It imports user-selected MATLAB (`.mat`) data, preserves provenance, and keeps morphology, ambiguity, quality, and parameter proposals on **separate scientific axes**.

> **Scientific status:** Output is a **candidate** morphology or parameter proposal compatible with image evidence. It does **not** establish a physical mechanism, replace expert scaling, or validate a model. Expert labels are human decisions, not ground truth. Development models and custom rules require independent, domain-appropriate validation before operational use. **ML Data Readiness** and **ML Dataset Manifests** are planning/governance surfaces only — they do **not** authorize model training. **ML-C has not started.**

![ML Dataset Manifests compact overview (English, ML-B.1d)](docs/assets/screenshots/ml-b1d/manifests_overview_en.png)

*ML Dataset Manifests — frozen synthetic Gate-F teaching example (compact layout). Gallery: `docs/assets/screenshots/ml-b1d/`.*

## Capabilities

- Local-first MAT import with inventory / data audit (source files are never rewritten)
- Ionogram viewer, temporal sequences, batch analysis, bilingual reports
- Python RuleEngine path by default (MATLAB Studio and Model Lab remain optional / non-default)
- Expert review corpora and campaigns with blind rounds, reveal/compare, and adjudication
- Disagreement analysis (descriptive; neither expert nor candidate is ground truth)
- **ML Data Readiness (ML-A.1a.2):** inventory, class coverage, sources/dates, contamination, holdout feasibility assessment, Readiness Gate A–F (F = ML-B planning only)
- **ML Dataset Manifests (ML-B.1d):** immutable role manifests, leakage-safe atomic groups, train / development / untouched-holdout reservation (workflow-sealed labels); still **no training**; **ML-C not started**
- EN/RU UI, Help, and documentation

## Module comparison

| Module | Purpose | Produces | Does **not** do |
|--------|---------|----------|-----------------|
| Import / Audit / Profile | Register MAT, inventory, instrument axes | Inventory / audit artifacts | Morphology classification |
| Viewer / Sequences | Inspect frames and time context | Display / contact sheets | Expert labels or training sets |
| Batch / Results | Default Python candidate pipeline | Candidate predictions + run provenance | Confirmed science / URSI scaling |
| Expert Review Corpora | Blind human reviews on frozen cohorts | Locked reviews, reveal/compare | Ground truth; training authorization |
| Expert Review Campaigns | Multi-date/source campaign operations | Campaign manifests / progress | Scientific validation claims |
| Disagreement Analysis | Describe expert↔candidate / expert↔expert patterns | Frozen descriptive snapshot + gate | Accuracy/F1; declare a winner |
| ML Data Readiness | Dataset/label readiness for a task contract | Frozen readiness audit + exports | Model training; final holdout manifests |
| ML Dataset Manifests | Leakage-safe train/dev/holdout identity reservation | Frozen manifest set + public exports | Model training; holdout unlock; ML-C |
| MATLAB Studio / Model Lab | Optional method / research prototyping | Studio or model-lab artifacts | Default automatic analysis |
| Rule Builder / Testing | Author and test versioned rule packs | Packs / test reports | External validation by itself |

## End-to-end user workflow

1. **Install or unpack** a writable workspace outside the install folder; choose EN or RU.
2. **Create or open a project** (Projects). Prefer `synthetic_data/` for first runs.
3. **Import MAT** without rewriting source; confirm **Instrument Profile**; run **Data Audit**.
4. **View** frames; optionally build temporal sequences.
5. **Run Batch Analysis** (default Python path); inspect **Results** as candidates only.
6. Build an **expert review corpus**, complete **blind** rounds, then reveal/compare (campaigns when operating across many sources/dates).
7. Optionally run **Disagreement Analysis** on revealed corpora (descriptive only).
8. Run **ML Data Readiness** for a chosen task contract; freeze an audit; read the Gate. Outcome **F** means ML-B *planning* only — still **no training**.
9. When Gate F permits, open **ML Dataset Manifests**, build atomic groups, reserve roles, freeze a manifest set (holdout labels remain sealed). Still **no training** / no ML-C.
10. Export bilingual reports / readiness / public manifest exports as needed. Keep research MAT and runtime audits out of git.

## Featured screenshots (ML-B.1d)

PNG captures at 1600×900 from the **ML-B.1d** UI with a sanitized synthetic Gate-F teaching example only. No owner private paths or credentials. Each scene has an EN and RU twin under `docs/assets/screenshots/ml-b1d/`.

<details>
<summary><strong>ML Dataset Manifests — compact overview</strong></summary>

![ML Dataset Manifests compact overview (English)](docs/assets/screenshots/ml-b1d/manifests_overview_en.png)

*Frozen teaching example — compact status, freeze status, Technical Details collapsed. RU: `manifests_overview_ru.png`.*

</details>

<details>
<summary><strong>Atomic Groups</strong></summary>

![Atomic Groups tab (English)](docs/assets/screenshots/ml-b1d/atomic_groups_en.png)

*Leakage-safe atomic groups — never split across roles. RU: `atomic_groups_ru.png`.*

</details>

<details>
<summary><strong>Role Assignment</strong></summary>

![Role Assignment tab (English)](docs/assets/screenshots/ml-b1d/role_assignment_en.png)

*Train / development / untouched holdout reservation (sealed targets when Frozen). RU: `role_assignment_ru.png`.*

</details>

<details>
<summary><strong>Coverage (human-readable)</strong></summary>

![Coverage tab (English)](docs/assets/screenshots/ml-b1d/coverage_en.png)

*Per-role item/group/sequence/date/source/target counts; shortened source IDs. RU: `coverage_ru.png`.*

</details>

<details>
<summary><strong>Holdout Reservation (frozen / sealed)</strong></summary>

![Holdout Reservation tab (English)](docs/assets/screenshots/ml-b1d/holdout_reservation_en.png)

*Holdout reserved; reference labels sealed; unlock in ML-B unavailable. RU: `holdout_reservation_ru.png`.*

</details>

<details>
<summary><strong>Manifest Summary</strong></summary>

![Manifest Summary tab (English)](docs/assets/screenshots/ml-b1d/validation_summary_en.png)

*Frozen summary — integrity / roles / protocol; no training claim. RU: `validation_summary_ru.png`.*

</details>

Prior readiness / home tour captures remain under [`docs/assets/screenshots/ml-a1a2/`](docs/assets/screenshots/ml-a1a2/) (not overwritten). Older page captures: [`docs/assets/screenshots/v1.1.1/`](docs/assets/screenshots/v1.1.1/).

## Quick start

See [User Guide (EN)](docs/USER_GUIDE_EN.md), [Installation](docs/INSTALLATION_EN.md). Portable: unpack, keep files together, use a writable workspace outside the install folder.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m ionogram_morphology_lab.app.main
```

Packaged EXE (when distributed): run `IonogramMorphologyLab.exe` from the portable folder. Current Build Identity: **ML-B.1d**.

1. Choose language · 2. New Project · 3. Start with `synthetic_data/` · 4. Follow Home recommended steps.

## Projects and MAT data

<details>
<summary><strong>Projects</strong></summary>

- **Purpose:** Create, open, and switch analysis projects safely.
- **When to use:** Before importing MAT data, or when changing workspace context.
- **Prerequisites:** Writable workspace path for create; existing project path for open.
- **Controls:** Current project card (name, path, created, last opened, active source, active run, unsaved changes); Open Project; Choose Project Folder; Open Recent Project; Remove from recent list; Create Project.
- **Effect:** Loads or creates project metadata; before switching — stops/resolves active jobs, warns about unsaved edits, clears stale UI state so results from two projects are never mixed.
- **Output:** Project directory and database rows; recent-projects list in settings.
- **Common mistake:** Creating inside the portable EXE folder; ignoring unsaved-change or active-job warnings.
- **Scientific limitation:** Project creation does not validate science.

</details>

- Projects store metadata, caches, runs, review corpora/campaigns, and readiness audits under the project tree.
- Import registers a user-selected `.mat` path; IML does not rewrite `Amp_all` or other source arrays.
- Prefer synthetic teaching files under `synthetic_data/` for demos and documentation.
- Keep owner research MAT, local databases, and generated review/readiness exports out of version control.

## Expert corpora, campaigns, and blind review

- **Expert Review Corpora** hold frozen cohorts, blind reviews, reveal/compare outcomes, and optional adjudication.
- **Expert Review Campaigns** organize multi-source / multi-date pilot operations without claiming scientific validation.
- Blind rounds must complete before reveal; candidate labels must not leak into blind views.
- Corrected reviews are revisions with provenance — not independent second opinions unless a distinct reviewer/round is recorded.

## Disagreement analysis

Read-only descriptive layer above revealed corpora/campaigns (`iml-disagreement-analysis-0.1.0`). It summarizes transitions and strata and records an analyst decision gate. It does **not** treat expert or candidate as ground truth and does not produce accuracy metrics.

![Disagreement Analysis (English)](docs/assets/screenshots/ml-a1a2/disagreement_analysis_en.png)

*Disagreement Analysis — selection/freeze tab; synthetic cohort `demo_pilot_example`.*

## ML Data Readiness (ML-A.1a.2)

Protocol: `iml-ml-dataset-readiness-0.1.0`. Shadow-only audit and governance:

- Inventory of expert-labelled items for a task contract (A–D family)
- Class coverage, missingness, reviewer independence
- Contamination checks (development-exposed items, related-frame groups, sequences)
- Holdout **feasibility assessment** (not a final holdout dataset)
- Readiness Gate outcomes A–F; **F authorizes ML-B manifest planning only**
- Always: `authorizes_training=False`; no accuracy/F1/sensitivity/specificity claims

![ML Data Readiness (English)](docs/assets/screenshots/ml-a1a2/ml_data_readiness_en.png)

*ML Data Readiness — Selection and Freeze. Caption on page states audit limits.*

## ML Dataset Manifests (ML-B.1d)

Protocol: `iml-ml-dataset-manifests-0.1.0`. Shadow-only planning above a frozen readiness audit:

- Deterministic leakage graph → **atomic groups** that must never split across dataset roles
- Roles: **train**, **development**, **untouched holdout**, excluded (identity reservation only — not training)
- Final freeze only when readiness Gate is **F** (planning-only); non-F audits allow draft simulation and correctly block freeze
- Public holdout identity manifest without item-level targets; reference labels are **workflow-sealed** (not cryptographic secrecy); ML-B cannot unlock them
- Always: `authorizes_training=False`; **ML-C not started**; no accuracy/F1 claims

### Scenario A — scientifically blocked pilot (example)

A one-sequence, fully development-exposed pilot (acquisition date `2014-10-15`) correctly yields **no untouched holdout groups** and **blocks freeze**. That is expected science, not a software failure.

### Scenario B — synthetic Gate F (teaching example only)

README screenshots use a **sanitized synthetic Gate-F teaching example** (multi-sequence, multi-date). Illustrative frozen counts: train 4 items / 4 groups; development 2 / 2; untouched holdout 3 / 2; Integrity PASS. It is **not** a scientific claim about any research corpus and does **not** authorize training.

## Integrity and contamination posture

- Candidate labels are excluded from expert target distributions used for readiness coverage.
- Development-exposed disagreement items cannot enter an untouched holdout assessment as clean.
- Related-frame groups / sequences are not treated as randomly splittable units.
- Frozen audits are immutable; corrected revisions get a new audit identity and preserve the parent.
- Acquisition dates use documented authority order; frame clock times are not treated as source dates.
- Exports strip absolute owner paths where the readiness/disagreement contracts require it.

## Installation and launch (verified paths)

| Path | Notes |
|------|--------|
| Dev: `pip install -e ".[dev]"` then `python -m ionogram_morphology_lab.app.main` | Verified for contributors |
| Portable packaged EXE | Unpack folder; run EXE; writable workspace outside install dir |
| MATLAB | Optional; not required for default Python analysis |

## Development and verification

Common checks (from a clean env with project deps):

```bash
python -m pytest
python scripts/validate_feature_registry_v2.py
python scripts/validate_synthetic_geometry_v2.py
python scripts/validate_ml_dataset_readiness.py
python scripts/validate_ml_dataset_manifests.py
python scripts/validate_morphology_disagreement_analysis.py
python scripts/validate_i18n.py
python scripts/validate_docs.py
python scripts/check_repository_hygiene.py
```

Release-gate evidence for **ML-B.1d**: **834** pytest passed; all release validators + hygiene OK; owner visual QA PASS; accepted EXE SHA-256 `132242FAFAA5C30D09C8FAE13C0795CEECD6B7CDDDB68CC56C0CCC03C4C32E80`. See [`docs/MLB1_FINAL_RELEASE_GATE_REPORT.md`](docs/MLB1_FINAL_RELEASE_GATE_REPORT.md).

## Repository structure (high level)

| Path | Role |
|------|------|
| `src/ionogram_morphology_lab/` | Application package (UI, analysis, readiness, review) |
| `scripts/` | Validators and maintenance utilities |
| `tests/` | Pytest suite |
| `docs/` | Guides, acceptance reports, screenshot assets |
| `synthetic_data/` | Teaching MAT files |
| `rule_packs/` | Versioned scientific rule packs |
| `dist/` | Local packaged builds (not committed) |

## Runtime and git safety

Do **not** commit: owner MAT files, `review_dataset/` runtime data, readiness/disagreement exports, local workspaces, caches, `build/`, `dist/`, personal settings, credentials. Prefer the inclusion lists in phase acceptance / final gate reports.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Viewer empty | Project + MAT + profile; rebuild cache after audit |
| Batch did not use MATLAB/ML | Default path is Python RuleEngine — expected |
| Blind reveal blocked | Complete required blind round first |
| Readiness Gate not F / not training | Training is never authorized; F is planning-only |
| Progress stuck after freeze | ML-A.1a.2 requires success at 100% with Cancel disabled — update to this build |
| Paths look absolute in exports | Use contract export actions; keep research data out of git |

## Roadmap

- **Done:** ML-A.1 → ML-A.1a.2 dataset readiness (shadow-only).
- **Done (this release):** **ML-B.1 → ML-B.1d** immutable dataset manifests and leakage-safe role reservation (shadow-only; no training).
- **Not started:** **ML-C** (any model experiment / training workflow).
- MATLAB Studio / Model Lab remain optional research surfaces, not default analysis.

## Documentation map

| Document | Role |
|----------|------|
| [USER_GUIDE_EN.md](docs/USER_GUIDE_EN.md) | Complete control reference |
| [USER_GUIDE_EN.md](docs/USER_GUIDE_EN.md) | Full control reference |
| [SCIENTIFIC_DECISION_MAP.md](docs/SCIENTIFIC_DECISION_MAP.md) | Default analysis path |
| [MLB1_FINAL_RELEASE_GATE_REPORT.md](docs/MLB1_FINAL_RELEASE_GATE_REPORT.md) | ML-B.1d release gate |
| [MLA1_FINAL_RELEASE_GATE_REPORT.md](docs/MLA1_FINAL_RELEASE_GATE_REPORT.md) | Prior ML-A.1a.2 release gate |

## License / citation

See repository `LICENSE` and science claim packs. Cite IML version **1.1.1** with Build Identity **ML-B.1d** and the analysis run id from Reports when reproducing a run.
