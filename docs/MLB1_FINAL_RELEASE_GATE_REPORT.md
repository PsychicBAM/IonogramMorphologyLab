# ML-B.1 → ML-B.1d Final Release Gate Report

**Branch:** `phase/ml-b1-dataset-manifests`
**Date:** 2026-08-08
**Final Build Identity:** `ML-B.1d`
**Accepted EXE SHA-256:** `132242FAFAA5C30D09C8FAE13C0795CEECD6B7CDDDB68CC56C0CCC03C4C32E80`
**Mode:** Shadow-only. **No commit. No push.** ML-C **not started**. No model training.

## Phase trail

| Phase | Focus | Outcome |
| --- | --- | --- |
| ML-B.1 | Immutable dataset manifests, leakage-safe roles, Gate-F freeze | Baseline |
| ML-B.1a | Acquisition-date authority, live RU↔EN, localized blockers, graph UX | Owner QA |
| ML-B.1b | Metric-scan false positives, holdout group counts, Validate lifecycle/UX | Owner QA |
| ML-B.1c | Collapsible context/Technical Details, workspace stretch, frozen holdout wording | Owner QA |
| ML-B.1d | Freeze-status consistency, human-readable Coverage | **Owner visual QA PASS** |

## Owner visual QA

**PASS** (owner-verified on Build Identity `ML-B.1d`, EXE SHA above).

Confirmed by owner:

- Scenario A remains Gate A / draft-only / freeze blocked; acquisition date `2014-10-15`; one protected atomic group; development-exposed cannot enter untouched holdout
- Scenario B legitimate Gate F with analyst rationale; roles train 4/4, development 2/2, holdout 3/2; Integrity PASS; Frozen; sealed public holdout; no ML-B unlock; Export available; frozen controls disabled
- RU/EN live refresh; collapsible panels; human-readable Coverage; no training; ML-C not started

## Full pytest

Command: `python -m pytest`

| Metric | Result |
| --- | --- |
| Passed | **834** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** (summary: `834 passed`; 834 collected) |
| Unexpected xpass | **0** |
| Duration | 614.03 s (~10 min 14 s) |

Warnings: none reported in the `-q` summary line. Environment may emit the pre-existing `pytest-asyncio` loop-scope deprecation when `-W default` is used; not introduced by ML-B.1d product code.

No product source fix was required after the full suite → **no rebuild**; Build Identity remains `ML-B.1d` with the accepted EXE SHA above.

## Release validators

| Validator | Result |
| --- | --- |
| `validate_feature_registry_v2.py` | OK (93/93) |
| `validate_synthetic_geometry_v2.py` | OK (`iml2-0.2.0`) |
| `validate_feature_shadow_mode.py` | OK |
| `validate_morphology_candidate_shadow.py` | OK |
| `validate_morphology_review_corpus.py` | OK |
| `validate_morphology_review_campaign.py` | OK |
| `validate_morphology_disagreement_analysis.py` | OK (`iml-disagreement-analysis-0.1.0`) |
| `validate_ml_dataset_readiness.py` | PASS (`iml-ml-dataset-readiness-0.1.0`) |
| `validate_ml_dataset_manifests.py` | OK (`iml-ml-dataset-manifests-0.1.0`) |
| `validate_i18n.py` | OK |
| `validate_docs.py` | PASS |
| `check_repository_hygiene.py` | **0** violations |

## Scientific contract audit

| Contract | Status |
| --- | --- |
| Shadow-only posture (`shadow_only=True`) | Active |
| `scientifically_validated` | False |
| Model trained | **No** |
| New ML runtime dependency | **No** |
| ML-C started | **No** |
| Production RuleEngine wired for ML | Unchanged / not used for ML-B |
| Candidate engine | `iml-morph-candidate-0.1.1` (unchanged) |
| Feature / geometry | `iml2-0.2.0` (unchanged) |
| Manifest protocol | `iml-ml-dataset-manifests-0.1.0` |
| Readiness protocol | `iml-ml-dataset-readiness-0.1.0` |
| Disagreement protocol | `iml-disagreement-analysis-0.1.0` |
| Candidate labels used for split assignment | **No** |
| Corrected reviews as independent reviewers | **No** |
| Development-exposed → untouched holdout | **Forbidden** (enforced) |
| Atomic groups across roles | **Never** |
| Random sequence split | **Never** |
| Gate F authorizes | ML-B planning only |
| ML-B authorizes training | **False** |
| Holdout reference labels | Workflow-sealed |
| ML-B unlock | **Unavailable** |
| Public holdout item-level targets | **Absent** |
| Accuracy/F1/sensitivity/specificity claims | **None introduced** |

## Regression hotspot audit

### Scenario A

- Fresh/current manifest acquisition date resolves to **2014-10-15**
- One protected sequence → one atomic group
- No untouched-eligible groups for holdout; freeze blocked
- Validation failure explicit and scientifically correct (Gate ≠ F / contamination)

### Scenario B (on-disk owner fixture + suite)

| Metric | Value |
| --- | --- |
| Items | 9 |
| Atomic groups | 8 |
| Train | 4 items / 4 groups |
| Development | 2 items / 2 groups |
| Untouched holdout | 3 items / 2 groups |
| Integrity | PASS |
| Lifecycle | Frozen |
| Public holdout identities | 3 (no target labels) |
| Unlock in ML-B | False |
| Export excludes reference labels | Yes |
| Reopen restores frozen set | Yes (owner + suite) |

### UI (ML-B.1c/1d)

- Frozen never shows “run Validate”
- Technical Details / context collapsible; defaults collapsed
- Coverage normal UI has no raw known canonical keys; full hashes in Technical Details
- RU↔EN live; frozen mutation controls disabled; Export available

## Build status

| Field | Value |
| --- | --- |
| Build Identity | `ML-B.1d` |
| Accepted EXE SHA-256 | `132242FAFAA5C30D09C8FAE13C0795CEECD6B7CDDDB68CC56C0CCC03C4C32E80` |
| Rebuild after full pytest | **Not required** (no product source fix) |

## README / screenshots (post-gate)

Updated after green gate:

- `README.md` / `README_RU.md` → current documented state **ML-B.1d**
- Gallery: `docs/assets/screenshots/ml-b1d/` (EN/RU twins; historical `ml-a1a2/` preserved)

## Commit / push

**Not performed** in this gate. Staging deferred to a separate owner-requested commit step.

## ML-C

**Not started.**
