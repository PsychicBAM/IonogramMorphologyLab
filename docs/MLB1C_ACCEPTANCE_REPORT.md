# ML-B.1c Acceptance Report — Collapsible Layout & Frozen Holdout Consistency

**Build Identity:** `ML-B.1c`
**Manifest protocol:** `iml-ml-dataset-manifests-0.1.0` (unchanged)
**Readiness protocol:** `iml-ml-dataset-readiness-0.1.0` (unchanged)
**Disagreement protocol:** `iml-disagreement-analysis-0.1.0` (unchanged)
**Mode:** Shadow-only. No training. ML-C not started. No commit/push.

## Owner UI findings addressed

1. **Technical Details** permanently consumed too much vertical space → collapsible, default **collapsed**.
2. **Manifest context / scientific status** block compressed the main workflow → collapsible with always-visible compact summary.
3. After freeze, Validation/Holdout text could still say **“Draft holdout assignment (not reserved)”** → lifecycle-specific wording using authoritative freeze + holdout lock state.

## Implementation

### Collapsible Manifest context

- Always-visible compact line, e.g.
  `Frozen · Gate F · Spread-F morphology · 9 items / 8 groups`
  RU: `Заморожен · Gate F · Морфология Spread-F · 9 элементов / 8 групп`
- Checkable `QGroupBox` (default collapsed) titled
  **Manifest context and scientific status** / **Контекст манифеста и научный статус**
- Expanded body keeps disclaimer, IDs, full Gate/contract labels, authorization flags, protocol.
- Critical blockers (Gate ≠ F, integrity fail, stale validation, missing frozen lock) remain in the always-visible alert/status area when the context panel is collapsed.

### Collapsible Technical Details

- Checkable `QGroupBox`, default collapsed; content widget hidden until expanded.
- Existing hashes/IDs/raw codes preserved; scroll retained when expanded.
- Session-only expand prefs; not written into scientific snapshots.

### Workspace sizing

- List boxes capped; tabs use expanding size policy + stretch factor 1.
- When both panels collapse, central tabs reclaim vertical space.
- Atomic Groups / Role Assignment: numeric/role columns size-to-contents; sequences/dates/contamination stretch; opaque IDs interactive with tooltips (elide middle).

### Frozen holdout wording

| Lifecycle | Wording |
| --- | --- |
| Draft / Validated | `Draft holdout assignment (not reserved): items=…, groups=…` |
| Frozen + valid lock | `Holdout reserved: items=…, groups=…` |
| Frozen + missing/corrupt lock | Integrity warning (fail closed); never claims reserved |

Validation tab uses the same lifecycle-aware wording (fixes simultaneous draft+reserved inconsistency).

### Frozen immutability UI

- Title/description/analyst/seed/policy disabled when Frozen.
- Leakage / Propose / Validate / Freeze disabled.
- Export and Refresh remain available.
- Expand/collapse does not mutate `manifest_set.json`.

## Tests

`tests/test_mlb1c_layout_holdout_ui.py` — 13 focused UI/behavior tests (default collapsed, expand/collapse, compact line, blockers when collapsed, tab space, selection preserve, RU↔EN labels, reserved vs draft wording, corrupt lock, frozen controls, no scientific mutation).

Regressions run: ML-B.1b validation, ML-B.1 manifests, ML-B.1a UX, ML-A.1a.2 worker lifecycle — pass.

Warning audit on `test_mlb1c_*`: only pre-existing `pytest-asyncio` config deprecation (not introduced by this patch).

## Validators / hygiene

| Check | Result |
| --- | --- |
| `validate_ml_dataset_manifests.py` | OK |
| `validate_ml_dataset_readiness.py` | PASS |
| `validate_i18n.py` | OK |
| `validate_docs.py` | PASS |
| `check_repository_hygiene.py` | 0 violations |

## Build

| Field | Value |
| --- | --- |
| Build Identity | `ML-B.1c` |
| Prior EXE SHA-256 (ML-B.1b) | `1316367BEFB7B90E7F0C5F14A06221AD671034595CB6DE6A6C4B28EFAC84E58C` |
| New EXE SHA-256 | `8969243F66D5D966C2B98772ACBE6636C802DC2C3A2BA2C9F1D1198EBD3B9D9C` |

## Owner visual QA required

Packaged smoke on Scenario B (`workspaces/MLB1A_ScenarioB_GateF_QA`) and brief Scenario A Gate-A blocker visibility.
Final full pytest **deferred** until owner visual QA.
No README screenshot refresh yet.
No commit / no push. ML-C not started.
