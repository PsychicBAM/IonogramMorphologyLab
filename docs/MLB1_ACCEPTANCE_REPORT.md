# ML-B.1 Acceptance Report — Immutable Dataset Manifests

**Branch:** `phase/ml-b1-dataset-manifests`
**Build Identity:** `ML-B.1`
**Manifest protocol:** `iml-ml-dataset-manifests-0.1.0`
**Readiness protocol (preserved):** `iml-ml-dataset-readiness-0.1.0`
**Mode:** Shadow-only. No training. No ML-C. No commit. No push.

## Purpose

ML-B.1 adds a read-only planning and governance layer above a frozen ML-A readiness audit:

- immutable identity manifests;
- leakage-safe atomic groups;
- train / development / untouched-holdout / excluded role reservation;
- overlap and integrity reports;
- sealed holdout reference labels (workflow sealing, not cryptography).

## Non-goals

Does **not** train, fit, fine-tune, evaluate, or deploy models. Does not add TensorFlow/PyTorch/CUDA. Does not unlock holdout labels. Does not wire the production RuleEngine. Does not claim accuracy/F1/ground truth. Does not start ML-C.

## Input authority

Authoritative input: frozen or gate-recorded ML-A readiness audit.
Final freeze requires Gate outcome **F** (`F_ready_for_mlb_manifest_planning_only`) with `authorizes_mlb_manifest_planning_only=True`.
Non-F audits: draft simulation allowed; holdout reservation and final freeze blocked — scientifically correct, not a software failure.

## Implementation

| Area | Location |
| --- | --- |
| Domain | `src/ionogram_morphology_lab/ml_dataset_manifests/` |
| UI | `src/ionogram_morphology_lab/ui/ml_dataset_manifests_page.py` |
| Nav | Methods → ML Dataset Manifests / Манифесты наборов данных ML |
| Validator | `scripts/validate_ml_dataset_manifests.py` |
| Tests | `tests/test_mlb1_*.py` |
| Runtime storage | `{project}/review_dataset/ml_manifests/` (gitignored) |

## Focused verification

| Check | Result |
| --- | --- |
| `pytest tests/test_mlb1_*` | **PASS** (13) |
| Warning audit (`-W default`) | Only pre-existing `pytest-asyncio` env deprecation |
| High-risk MLA1 / disagreement / corpus / campaign regressions | **PASS** after identity bump |
| `validate_ml_dataset_manifests.py` | **OK** |
| `validate_ml_dataset_readiness.py` | **OK** |
| Disagreement / corpus / campaign validators | **OK** |
| `validate_i18n.py` | **OK** |
| `validate_docs.py` | **PASS** |
| Hygiene | **0** |
| Full pytest | **deferred** until after owner visual QA |

## Packaged smoke (required before release)

Scenario A — blocked pilot (one sequence, all development-exposed, non-F): draft OK; holdout/freeze blocked; no random split.
Scenario B — synthetic Gate F multi-sequence: leakage graph, reproducible proposal, freeze, sealed holdout, export without new set / without reference labels.

## EXE

| Item | Value |
| --- | --- |
| Path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` |
| SHA-256 | `E773F21BFB23650535D81719BBB3D196E7C168A2455297FD4F3C0E122C429C8B` |
| Differs from ML-A.1a.2 | **yes** (prior `67FBB83E6BCECF2A58C719A57AF5E60B9E74FCB31EB1FC130B8BD8DAE6A6A246`) |

## Packaged smoke

Automated unit/integration coverage exercises blocked-pilot and Gate-F freeze paths. Owner visual QA on the packaged EXE remains required for Scenarios A and B (see `docs/MLB1_OWNER_QA.md`).

## Status

- Owner visual QA: **required**
- Full pytest: **deferred** until after owner visual QA
- Commit / push: **not performed**
- ML-C: **not started**
