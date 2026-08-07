# ML-B.1b Acceptance Report — Validation Integrity, Holdout Groups, Validate UX

**Branch:** `phase/ml-b1-dataset-manifests`
**Build Identity:** `ML-B.1b`
**Manifest protocol (unchanged):** `iml-ml-dataset-manifests-0.1.0`
**Readiness protocol (unchanged):** `iml-ml-dataset-readiness-0.1.0`
**Disagreement protocol (unchanged):** `iml-disagreement-analysis-0.1.0`
**Mode:** Shadow-only. No training. No ML-C. No commit. No push.

## Owner findings (inputs)

Scenario A: **PASS** (unchanged scientifically).
Scenario B opened successfully after fixture repair, with Gate F / rationale / planning-only / seed-42 roles, but three release blockers remained:

1. Validate had no clear completion/result feedback.
2. Forbidden-metric detection false-positived on substring `"f1"` inside hashes/IDs.
3. Holdout Reservation showed `items=3, groups=0` while Coverage showed holdout `atomic_groups=2`.
4. Lifecycle could show `Validated` while Integrity OK was No.

## Root causes

1. **Forbidden metrics** — `validate_freeze_eligibility` dumped item JSON to lowercase text and used substring `metric in blob` for `"f1"` / `"accuracy"` / `"ground_truth"`. Hex digits inside `atomic_group_id` (e.g. `…cf1745…`) matched `"f1"`.
2. **Holdout groups=0** — Rebuild Leakage Graph created new `AtomicGroup` rows with default `role=excluded` while **items kept** prior `role=untouched_holdout`. Holdout UI counted `g.role`; Coverage `item_level` counted unique `item.atomic_group_id`. Stale `group_coverage.json` worsened the mismatch. Freeze used group roles → `holdout_not_reserved`.
3. **Validated + Integrity No** — `validate()` promoted draft→validated only on success, but **never reverted** `validated` when a later validation failed. UI read `report["ok"]` independently from lifecycle.

## Fixes

| Area | Change |
| --- | --- |
| Metric scan | New `metric_scan.py`: key-aware recursive JSON inspection; opaque ID/hash keys skipped; claim phrases only on claim-bearing fields |
| Holdout groups | `sync_group_roles_from_items` after leakage/coverage/validate; holdout UI counts unique holdout `atomic_group_id`; group_role_counts from items |
| Lifecycle | Success → `Validated` + `validated_content_hash` + `last_validation_ok=true`; failure → remain/revert `Draft`; mutations invalidate validation |
| Validate UX | Localized success/failure dialogs; Validation tab refresh; progress 100%; freeze enablement from same report |

## Scenario B expected (after fix)

Fixture: `workspaces/MLB1A_ScenarioB_GateF_QA` (gitignored; see `SCENARIO_B_META.json`).

| Field | Value |
| --- | --- |
| Audit ID | `readiness_673df6681fff` |
| Draft manifest | `manifest_4c688c08ae61` |
| Items / atomic groups | 9 / 8 |
| train | 4 items / 4 groups |
| development | 2 items / 2 groups |
| untouched_holdout | 3 items / 2 groups |
| Gate F | planning-only true; training false |
| After Validate | Integrity PASS; lifecycle Validated; Freeze enabled |
| After Freeze | public holdout 3 identities; no targets; reference sealed; unlock blocked |

Cohort id `scenario_b_ready_f1_005` contains `"f1"` deliberately — no salting to dodge checker bugs.

## Focused verification

| Check | Result |
| --- | --- |
| `pytest tests/test_mlb1b_validation_integrity.py -q` | **13 passed** |
| Warning audit `-W default` | Only pre-existing `pytest-asyncio` env deprecation |
| ML-B.1 / ML-B.1a / worker regressions | **38 passed** |
| Validators + hygiene | **all OK / PASS; hygiene 0** |
| Full pytest | **deferred** until owner visual QA |

## EXE

| Item | Value |
| --- | --- |
| Path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` |
| Build Identity | `ML-B.1b` |
| Prior ML-B.1a SHA | `B4D6D713E97F072534C5FDB0A997DF2F3D1ACB3074C173E1056B91B7EEF4ADAC` |
| New SHA-256 | `1316367BEFB7B90E7F0C5F14A06221AD671034595CB6DE6A6C4B28EFAC84E58C` |

## Status

- Owner visual QA: **required again** (especially Scenario B Validate → Freeze)
- Full pytest: **deferred**
- Commit / push: **not performed**
- ML-C: **not started**
- Runtime Scenario B fixture: **not staged**
