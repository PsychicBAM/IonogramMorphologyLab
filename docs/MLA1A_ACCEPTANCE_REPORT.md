# Phase ML-A.1a — Acceptance Report

**Mode:** Shadow-only. No training. No ML dependencies added.
**Branch:** `phase/ml-a1-dataset-readiness`
**Build Identity:** `ML-A.1a`
**Commit / push:** not performed (owner restriction).

## Owner QA findings (release blockers)

1. **RU localization incomplete** — normal page showed English strings and raw canonical codes (`selected_records`, `gate_recorded`, blocker codes, etc.).
2. **Saved audits not auto-loaded** — list stayed empty until freeze/export refreshed the page; no `project_changed` / `showEvent` wiring.
3. **Sources and Dates mis-mapped** — Source column used morphology; Date column used frame times; `unique_source_dates` counted times.
4. **Task-contract coverage ignored** — Class Coverage always showed morphology even for Assessability / Interference / Parameter-scaling contracts.

## Root causes

| Finding | Root cause |
| --- | --- |
| Localization | Hardcoded English form labels; overview/review/holdout/gate dumped raw keys; retranslate did not refresh populated tables. |
| Saved-audit reload | Page never connected `session.project_changed` / `events.project_changed`; no `showEvent` scan of `{project}/review_dataset/ml_readiness/`. |
| Source/Date | UI filled Sources tab from `morphology_x_source_date`; inventory fell back to `frame_time[:10]`, turning bare times into “dates”. |
| Task contract | `build_coverage_summary` always used morphology counts; UI always rendered `morphology_label_counts`. |

## Corrections

- Complete RU/EN i18n for readiness page (disclaimer, contracts, lifecycle, overview sections, coverage, sources, review note, missingness, contamination, holdout, gate, export/freeze/progress).
- Auto-reload saved audits on project change, page show, create/freeze/gate/export refresh; independent of corpus selection.
- Export requires a selected frozen/gate-recorded audit and does **not** create a new audit ID.
- Acquisition dates normalized to `YYYY-MM-DD` only; frame times stay in a separate Time column.
- Contract-specific Class Coverage targets (morphology / assessability+ambiguity / interference / unsupported parameter scaling).
- Frozen audit restores and renders its own task contract.
- Synthetic related-frame groups flagged; sequence correlation messaging; Technical Details collapsed for raw keys.
- Related-frame / sequence counts clarified so 13 frames in one sequence are not presented as 13 independent events.

## Owner-like fixture — corrected counts

| Metric | Expected |
| --- | --- |
| `raw_frame_count` | 13 |
| `unique_sources` | 1 |
| `unique_source_dates` | 1 |
| `unique_sequences` | 1 |
| Sources table | one source/date group, count 13; times ~04:59–06:59 separate |

Holdout feasibility for the exposed pilot remains scientifically unchanged when applicable:
`appears_possible = false`, `untouched_groups = 0` (pilot exposure case).

## Protocol versions (unchanged)

- `ml_dataset_readiness_protocol_version`: `iml-ml-dataset-readiness-0.1.0`
- `disagreement_analysis_protocol_version`: `iml-disagreement-analysis-0.1.0`

## Focused tests

```
python -m pytest tests/test_mla1a_* -q
python -W default -m pytest tests/test_mla1a_* -q
```

Also run: `tests/test_mla1_dataset_readiness.py`, disagreement analysis regressions.

**Full pytest:** deferred until after owner visual QA and before commit/push.

## Validators / hygiene

| Check | Result |
| --- | --- |
| `validate_ml_dataset_readiness.py` | OK |
| `validate_morphology_disagreement_analysis.py` | OK |
| `validate_morphology_review_corpus.py` | OK |
| `validate_i18n.py` | OK |
| `validate_docs.py` | PASS |
| `check_repository_hygiene.py` | 0 violations |

## Packaging

- Build Identity: **ML-A.1a**
- Previous EXE SHA-256: `0743C25CEED236E38C9400DAB3FDD0910D469F4BD77743CAC82629947A694BFE`
- New EXE SHA-256: `E13458DE37C5280A8B97EC51ABE1A4D0C85420A1A50777453A5CD21CD99CC569`

## Remaining gates

- Owner visual QA on packaged EXE (see `docs/MLA1_OWNER_QA.md`).
- One final full `pytest` before commit/push.
- **No commit. No push.**
