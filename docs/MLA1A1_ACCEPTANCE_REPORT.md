# Phase ML-A.1a.1 — Acceptance Report

**Mode:** Shadow-only. No training. No ML dependencies added.
**Branch:** `phase/ml-a1-dataset-readiness`
**Build Identity:** `ML-A.1a.1`
**Commit / push:** not performed (owner restriction).

## Owner finding

For source `Am_all_2014-10-15.mat` (13 frames, times 04:59–06:59, one sequence):

| Field | Observed (broken) | Expected |
| --- | --- | --- |
| Date column | `04:59`, `05:09`, … | `2014-10-15` |
| Time column | `04:59`, … | `04:59`, … |
| `unique_source_dates` | 13 | **1** |
| `unique_sources` | 1 | 1 |
| `unique_sequences` | 1 | 1 |

## Root cause

Inventory acquisition-date resolution looked up `grouping["source_date"]` (often absent on real cohort items, which store `grouping["date"]` / `datetime_metadata` / filename hints) and then **fell back to `frame_time`** (and historically `frame_time[:10]`).

Pilot frame times are bare HH:MM values such as `04:59`. Those values were stored and counted as distinct acquisition dates, so Sources/Dates showed time in the Date column and Overview reported `unique_source_dates = 13`.

Filename authority for `Am_all_2014-10-15.mat` → `2014-10-15` was not applied in the readiness inventory path.

## Date authority order (implemented)

1. Authoritative project/campaign source-inventory `date_hint`
2. Validated cohort grouping keys: `source_date`, `acquisition_date`, `date`
3. Validated MAT/source metadata (`datetime_metadata` when date-like)
4. Deterministic filename parse (`Am_all_2014-10-15.mat` → `2014-10-15`)
5. Explicit missing date (never invent from frame time)

**Never** derived from: frame time, frame index, review timestamp, file mtime, audit creation time.

Canonical identity: `YYYY-MM-DD`. Time-only values are rejected.

## Corrected owner-fixture counts

- `raw_frame_count = 13`
- `unique_sources = 1`
- `unique_source_dates = 1`
- `unique_frame_times = 13`
- `unique_sequences = 1`
- Sources table: Source `Am_all_2014-10-15.mat`, Acquisition Date `2014-10-15`, Frame Time `04:59`…`06:59`

## Legacy frozen audits

Immutable frozen inventories with time-as-date values are **not rewritten**.

- Detected via `diagnose_invalid_date_projection`
- Localized warning (RU/EN)
- Action: **Create Corrected Audit Revision** / «Создать исправленную ревизию»
- Revision re-projects from current authoritative metadata into a **new** audit ID; parent remains unchanged

## Task-contract visibility

- Selector remains on Selection and Freeze with label «Контракт задачи»
- Short explanation of target-label role
- Header/Overview shows «Контракт текущего аудита: …»
- Distinct from Readiness Gate controls

## Gate blocker B consistency

Blocker checkboxes are **manual**. Auto-suggestions (evidence-only) never suggest B when `missing_required_fields = 0` and the contract is supported. Manual selection of B remains allowed.

## Focused tests

```
python -m pytest tests/test_mla1a1_* -q
python -W default -m pytest tests/test_mla1a1_* -q
```

Also: `tests/test_mla1_dataset_readiness.py`, `tests/test_mla1a_readiness_fixes.py`.

**Full pytest:** deferred until after owner visual QA and before commit/push.

## Validators / hygiene

| Check | Result |
| --- | --- |
| readiness | OK |
| disagreement | OK |
| corpus | OK |
| i18n | OK |
| docs | PASS |
| hygiene | 0 |

## Packaging

- Build Identity: **ML-A.1a.1**
- Protocol versions unchanged:
  - `iml-ml-dataset-readiness-0.1.0`
  - `iml-disagreement-analysis-0.1.0`
- Previous EXE SHA-256: `E13458DE37C5280A8B97EC51ABE1A4D0C85420A1A50777453A5CD21CD99CC569`
- New EXE SHA-256: `BEB14E77837407BFED7038A6152C7BA11F1D68346117F56B688539A207BAA6AA`

## Remaining gates

- Owner visual QA on packaged EXE
- One final full pytest before commit/push
- **No commit. No push.**
