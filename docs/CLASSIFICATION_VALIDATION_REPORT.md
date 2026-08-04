# Classification Validation Report

**Scientific status:** candidate / development-calibrated — **NOT** independently validated.
**Acceptance:** FAIL for scientific PASS (insufficient owner-reviewed / expert-confirmed labels).

## Active methods (default pipeline)

| Component | Status |
|---|---|
| Preprocess / audit / segment / features | active |
| RuleEngine (RULE_PACK_IML1) | active, development-calibrated / engineering_default |
| Reference atlas | metadata-only similarity |
| MATLAB methods | optional, off by default |
| Development ML / ensemble | optional, off by default |
| Multi-frame temporal conclusion | optional when neighbor masks supplied |

## Labelled-frame count by category

| Category | Expert-confirmed | Owner-reviewed | Automatic-only (this audit) |
|---|---:|---:|---:|
| `clean` | 0 | 0 | 0 |
| `diffuse_unspecified` | 0 | 0 | 30 |
| `frequency_spread` | 0 | 0 | 0 |
| `range_spread` | 0 | 0 | 0 |
| `mixed_spread` | 0 | 0 | 0 |
| `interference_dominated` | 0 | 0 | 0 |
| `not_assessable` | 0 | 0 | 4 |
| `indeterminate` | 0 | 0 | 0 |

**Verdict:** insufficient labelled examples for per-class precision/recall claims.

## R005 changes

- R005 still fires as interference *evidence*.
- Morphology is **not** replaced by `interference_dominated` when a usable trace remains.
- Morphology becomes `not_assessable` only when interference **prevents assessment**.
- Interference level is recorded separately (`none|present|significant|dominant|prevents_assessment`).
- Frames in this audit with significant/dominant interference but assessable morphology: **16**.
- Frames that would previously be R005-suppressed at moderate dominance but now keep morphology: **0** (proxy count).

## Metrics

- Confusion matrix: **not reported** — insufficient labelled examples.
- Per-class precision/recall: **insufficient labelled examples**.
- Calibration status: **uncalibrated**.
- Abstention / uncertain rate: see automatic tables below.

## Automatic candidate counts

`{"diffuse_unspecified": 30, "not_assessable": 4}`

## Audit table — 2014-09-25

| Frame | Time | H | V | Inter level | Rules | Near-thr | Canonical | Display (RU) | Temporal | Review |
|------:|:----:|--:|--:|:-----------|:------|:---------|:----------|:-------------|:---------|:-------|
| 421 | 07:00 | 22.361 | 10.062 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 451 | 07:30 | 20.396 | 9.178 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 481 | 08:00 | 22.361 | 10.062 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 511 | 08:30 | 22.0 | 9.9 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 541 | 09:00 | 22.045 | 9.92 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 571 | 09:30 | 21.587 | 9.735 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 601 | 10:00 | 24.0 | 10.8 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 631 | 10:30 | 24.0 | 10.8 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 661 | 11:00 | 22.361 | 10.13 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 691 | 11:30 | 22.0 | 9.9 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |

### Focus rows (2014-09-25)

- **f421 07:00** → `diffuse_unspecified` (H=22.361, V=10.062, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f451 07:30** → `diffuse_unspecified` (H=20.396, V=9.178, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f481 08:00** → `diffuse_unspecified` (H=22.361, V=10.062, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f511 08:30** → `diffuse_unspecified` (H=22.0, V=9.9, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f541 09:00** → `diffuse_unspecified` (H=22.045, V=9.92, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f571 09:30** → `diffuse_unspecified` (H=21.587, V=9.735, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f601 10:00** → `diffuse_unspecified` (H=24.0, V=10.8, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f631 10:30** → `diffuse_unspecified` (H=24.0, V=10.8, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f661 11:00** → `diffuse_unspecified` (H=22.361, V=10.13, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f691 11:30** → `diffuse_unspecified` (H=22.0, V=9.9, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])

## Audit table — 2014-10-15

| Frame | Time | H | V | Inter level | Rules | Near-thr | Canonical | Display (RU) | Temporal | Review |
|------:|:----:|--:|--:|:-----------|:------|:---------|:----------|:-------------|:---------|:-------|
| 1201 | 20:00 | 0.8 | 0.8 | `prevents_assessment` | `R005` | `—` | `not_assessable` | Кадр невозможно надёжно оценить | `sudden_change_or_artifact_candidate` | automatic candidate; visual owner review pending |
| 1211 | 20:10 | 0.8 | 0.8 | `prevents_assessment` | `R005` | `—` | `not_assessable` | Кадр невозможно надёжно оценить | `sudden_change_or_artifact_candidate` | automatic candidate; visual owner review pending |
| 1221 | 20:20 | 0.8 | 0.8 | `prevents_assessment` | `R005` | `—` | `not_assessable` | Кадр невозможно надёжно оценить | `sudden_change_or_artifact_candidate` | automatic candidate; visual owner review pending |
| 1231 | 20:30 | 0.8 | 0.8 | `prevents_assessment` | `R005` | `—` | `not_assessable` | Кадр невозможно надёжно оценить | `sudden_change_or_artifact_candidate` | automatic candidate; visual owner review pending |
| 1241 | 20:40 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1251 | 20:50 | 18.439 | 7.801 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1261 | 21:00 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1271 | 21:10 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1281 | 21:20 | 19.698 | 8.864 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1291 | 21:30 | 20.0 | 9.0 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1301 | 21:40 | 20.0 | 9.0 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1311 | 21:50 | 20.0 | 9.0 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1321 | 22:00 | 14.0 | 6.037 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1331 | 22:10 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1341 | 22:20 | 18.654 | 8.864 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1351 | 22:30 | 20.0 | 9.0 | `present` | `—` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1361 | 22:40 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1371 | 22:50 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1381 | 23:00 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1391 | 23:10 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1401 | 23:20 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1411 | 23:30 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1421 | 23:40 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |
| 1431 | 23:50 | 20.0 | 9.0 | `significant` | `R005` | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип не определён | `continuation_candidate` | automatic candidate; visual owner review pending |

### Focus rows (2014-10-15)

- **f1201 20:00** → `not_assessable` (H=0.8, V=0.8, inter=prevents_assessment, flags=['interference_prevents_assessment'])
- **f1211 20:10** → `not_assessable` (H=0.8, V=0.8, inter=prevents_assessment, flags=['interference_prevents_assessment'])
- **f1221 20:20** → `not_assessable` (H=0.8, V=0.8, inter=prevents_assessment, flags=['interference_prevents_assessment'])
- **f1231 20:30** → `not_assessable` (H=0.8, V=0.8, inter=prevents_assessment, flags=['interference_prevents_assessment'])
- **f1241 20:40** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1251 20:50** → `diffuse_unspecified` (H=18.439, V=7.801, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1261 21:00** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1271 21:10** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1281 21:20** → `diffuse_unspecified` (H=19.698, V=8.864, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1291 21:30** → `diffuse_unspecified` (H=20.0, V=9.0, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f1301 21:40** → `diffuse_unspecified` (H=20.0, V=9.0, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f1311 21:50** → `diffuse_unspecified` (H=20.0, V=9.0, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f1321 22:00** → `diffuse_unspecified` (H=14.0, V=6.037, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1331 22:10** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1341 22:20** → `diffuse_unspecified` (H=18.654, V=8.864, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1351 22:30** → `diffuse_unspecified` (H=20.0, V=9.0, inter=present, flags=['interference_present', 'mixed_requires_both_balanced_axes', 'unbalanced_dual_axis_thickening'])
- **f1361 22:40** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1371 22:50** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1381 23:00** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1391 23:10** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1401 23:20** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1411 23:30** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1421 23:40** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])
- **f1431 23:50** → `diffuse_unspecified` (H=20.0, V=9.0, inter=significant, flags=['artifact_vs_real_trace', 'mixed_vs_interference', 'interference_significant', 'interference_present_morphology_still_assessable'])

## Remaining unsupported / incomplete

- No expert-confirmed gold labels in-repo.
- Reference atlas has no redistributed comparison images.
- Temporal onset/termination are heuristic mask-overlap notes only.
- Do not claim scientific PASS until owner-reviewed multi-class labels exist and are evaluated on a held-out date split.

Machine dump: `workspaces/_class_val_audit/audit.json`

