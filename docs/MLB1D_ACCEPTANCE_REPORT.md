# ML-B.1d Acceptance Report — Freeze Status & Coverage Presentation

**Build Identity:** `ML-B.1d`
**Manifest protocol:** `iml-ml-dataset-manifests-0.1.0` (unchanged)
**Readiness protocol:** `iml-ml-dataset-readiness-0.1.0` (unchanged)
**Disagreement protocol:** `iml-disagreement-analysis-0.1.0` (unchanged)
**Mode:** Shadow-only. No training. ML-C not started. No commit/push.

## Owner findings addressed

1. **Frozen Input Audit** still showed `Freeze blockers: (none yet — run Validate)` → lifecycle-aware freeze status.
2. **Coverage tab** rendered raw keys / Python-like lists / full SHA digests → human-readable role sections with localized labels and shortened source IDs.

## Freeze status (Input Audit)

| Lifecycle | Presentation |
| --- | --- |
| Draft (no blockers) | Freeze status: Validation has not been completed. |
| Validated (no blockers) | Freeze status: Validation passed. Manifest is eligible for freeze. |
| Frozen | Freeze status: Manifest is already frozen. No further freeze action is required. |
| Blocked | Freeze blockers: localized actual blockers |

Never shows “run Validate” for a Frozen manifest. Blocker codes / lifecycle model unchanged.

## Coverage presentation

Per role (Train / Development / Untouched holdout / Excluded):

- Items, Atomic groups, Sequences, Acquisition dates, Sources, Target classes (counts)
- Compact `Sequence | Acquisition date | Source` rows with shortened source IDs (`c211…1111`)
- Compact `Target class | Items` rows
- No raw keys (`unique_items`, `atomic_groups`, `acquisition_dates`, `target_distribution`, …) in normal UI
- Full SHA-256 and raw JSON remain in Technical Details (`group_coverage.json`)

## Frozen holdout tab

```
Holdout reserved
Items: 3
Atomic groups: 2
Reference labels: sealed
Unlock in ML-B: unavailable
```

RU mirrors the same structure. No draft/not-reserved wording for a valid Frozen lock.

## Tests

`tests/test_mlb1d_freeze_coverage_ui.py` — **12 passed**

Regressions: ML-B.1c UI, 1b validation, manifests, 1a UX — **53 passed**

Warning audit: only pre-existing `pytest-asyncio` config deprecation.

## Validators / hygiene

All OK / PASS; hygiene **0**.

## Build

| Field | Value |
| --- | --- |
| Build Identity | `ML-B.1d` |
| Prior EXE SHA-256 (ML-B.1c) | `8969243F66D5D966C2B98772ACBE6636C802DC2C3A2BA2C9F1D1198EBD3B9D9C` |
| New EXE SHA-256 | `132242FAFAA5C30D09C8FAE13C0795CEECD6B7CDDDB68CC56C0CCC03C4C32E80` |

## Owner visual QA required

Packaged smoke on frozen Scenario B + brief Scenario A.
Final full pytest **deferred**. No README screenshot refresh. No commit/push. ML-C not started.
