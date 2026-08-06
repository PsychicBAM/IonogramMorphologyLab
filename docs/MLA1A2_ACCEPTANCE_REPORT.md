# Phase ML-A.1a.2 — Acceptance Report

**Mode:** Shadow-only.
**Build Identity:** `ML-A.1a.2`
**Commit / push:** not performed.

## Owner finding

After a successful readiness freeze, status showed «Аудит готовности заморожен» while the progress bar remained at **66%**.

## Root cause

Projection progress used `100 * i / total` and never emitted a final **100%** after freeze write/integrity completed. The success handler updated status text but did not force the progress bar to 100%.

## Fix

- `freeze_audit` / revision freeze emits `progress_cb(100, …)` on success.
- Projection progress reserved below 100% (tops at 90%) until write completion.
- UI success path always sets progress to **100%**, disables Cancel, sets localized success status.
- Cancellation never shows 100% or success.
- Failure preserves last progress and shows localized error.
- Duplicate `finished_ok` ignored; worker/thread cleaned safely.
- Same lifecycle for freeze, corrected revision (background worker), and export.

## Protocol versions (unchanged)

- `iml-ml-dataset-readiness-0.1.0`
- `iml-disagreement-analysis-0.1.0`

## Focused tests

`tests/test_mla1a2_progress_lifecycle.py` — success@100%, no success with progress&lt;100%, cancel/fail, duplicate finish, no lingering QThread, RU/EN.

**Full pytest:** deferred until after owner visual QA / before commit.

## Validators / hygiene

readiness OK · i18n OK · docs PASS · hygiene 0

## Packaging

- Previous EXE SHA-256: `BEB14E77837407BFED7038A6152C7BA11F1D68346117F56B688539A207BAA6AA`
- New EXE SHA-256: `67FBB83E6BCECF2A58C719A57AF5E60B9E74FCB31EB1FC130B8BD8DAE6A6A246`

## Remaining

Owner visual QA required. No commit. No push.
