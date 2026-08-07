# ML-B.1a Acceptance Report — Date Projection, Live i18n, Graph Feedback, Scenario B Fixture

**Branch:** `phase/ml-b1-dataset-manifests`
**Build Identity:** `ML-B.1a`
**Manifest protocol (unchanged):** `iml-ml-dataset-manifests-0.1.0`
**Readiness protocol (unchanged):** `iml-ml-dataset-readiness-0.1.0`
**Disagreement protocol (unchanged):** `iml-disagreement-analysis-0.1.0`
**Mode:** Shadow-only. No training. No ML-C. No commit. No push.

## Owner Scenario A

Owner visual QA for Scenario A scientific core: **PASS** (prior owner session).

Corrected coverage for the 21-frame pilot remains:

| Field | Expected |
| --- | --- |
| unique_items | 21 |
| sources | 1 |
| acquisition_dates | `["2014-10-15"]` |
| sequences | 1 |
| atomic_groups | 1 |
| development_exposed_items | 21 |
| eligible_untouched_groups | 0 |
| can_draft / can_freeze | true / false |
| authorizes_training / authorizes_mlc | false / false |

## Scenario B fixture repair (this task)

### Root cause

The documented Scenario B folder `workspaces/MLB1A_ScenarioB_GateF_QA` was populated with readiness/manifest runtime data **without** creating a normal IML project. It therefore lacked `project.json` (and `project.sqlite`). The packaged app correctly refused to open it («В папке нет project.json.»). This was a **fixture initialization defect**, not an app validation defect.

### Repair

- Regenerated via official `ionogram_morphology_lab.projects.model.create_project` (same path as Projects → Create Project).
- Relocated to stable folder `workspaces/MLB1A_ScenarioB_GateF_QA` with synced `project.json` `root`.
- Populated with real ML-A freeze + holdout feasibility + `record_gate` (non-empty rationale) and ML-B draft (seed 42).
- Broken prior folder preserved at `workspaces/MLB1A_ScenarioB_GateF_QA_broken_no_project_json` (gitignored).
- Product source for open-project validation: **unchanged**.
- EXE: **not rebuilt**; SHA remains `B4D6D713E97F072534C5FDB0A997DF2F3D1ACB3074C173E1056B91B7EEF4ADAC`.

### Current openable fixture (README/META are source of truth)

| Field | Value |
| --- | --- |
| Project folder | `workspaces/MLB1A_ScenarioB_GateF_QA` |
| Project name | MLB1A Scenario B Gate F QA |
| Readiness audit ID | `readiness_600fe059b399` |
| Draft manifest ID | `manifest_249607191260` |
| Title | MLB1A Scenario B — Gate F synthetic ready |
| Task contract | Spread-F morphology classification |
| Gate | F |
| Rationale | Independent sequences, acquisition dates, and classes support class-aware group-separated holdout reservation for ML-B planning only; no training authorized. |
| Scale | items 9; sources 8; dates 8; sequences 8; atomic groups 8; untouched-eligible groups 8; development-exposed 0 |
| Seed 42 roles | train 4 / development 2 / untouched_holdout 3 (public holdout items 3) |
| authorizes_mlb_manifest_planning_only | true |
| authorizes_training | false |

### Pre-owner smoke (domain + open-path)

Automated smoke (`workspaces/_mlb1a_tools/smoke_scenario_b_open_and_mlb.py`) confirmed:

- `project.json` present; load matches app folder-open check;
- Gate F + rationale + planning-only / training=false;
- draft roles and 8 groups;
- freeze/seal/export/unlock-blocked/reopen on a disposable copy.

**Scenario B owner visual QA on the packaged EXE is still required — not claimed PASS.**

### Product defect discovered (not patched)

While validating freeze on the fixture, ML-B integrity reported `prohibited_metric_payload:f1` because the checker uses a naive substring search for `"f1"` inside item JSON, which matches hex digits inside `atomic_group_id` (e.g. `…cf1745…`). This is a **genuine product defect**.

Per fixture-only policy: **product code was not changed**. The fixture builder cohort-id-salts until group-id hexes avoid the false positive so owner freeze can proceed. A follow-up product fix should use key-aware / token-aware metric detection (not substring-in-hex).

## Gate F clarification (unchanged)

Outcome F still requires explicit analyst rationale; integrity alone does not authorize F. Scenario A pilot must not be forced to F.

## Focused verification (prior ML-B.1a patch)

Recorded in the previous ML-B.1a acceptance pass (`tests/test_mlb1a_manifest_ux_dates.py`, validators, hygiene). This fixture-repair task did **not** rerun full pytest and did **not** rebuild the EXE.

## Docs / hygiene (this repair)

| Check | Result |
| --- | --- |
| `validate_docs.py` | recorded at completion |
| `check_repository_hygiene.py` | recorded at completion |
| `git diff --check` | recorded at completion |

## EXE

| Item | Value |
| --- | --- |
| Path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` |
| Build Identity | `ML-B.1a` |
| SHA-256 | `B4D6D713E97F072534C5FDB0A997DF2F3D1ACB3074C173E1056B91B7EEF4ADAC` |
| Rebuilt for fixture repair | **no** |

## Status

- Scenario A owner QA: **PASS** (prior)
- Scenario B owner QA: **not claimed** — fixture now openable; owner must re-run EXE steps
- Full pytest: **not rerun** (fixture/docs-only policy)
- Commit / push: **not performed**
- ML-C: **not started**
- Runtime Scenario B fixture: **not staged** (`workspaces/`)
