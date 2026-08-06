# Phase ML-A.1 / ML-A.1a / ML-A.1a.1 — Owner QA Checklist

ML dataset readiness audit — **not** a scientific validation study and **not** model training.

**Expected Build Identity:** `ML-A.1a.2`
**Packaged EXE SHA-256:** `67FBB83E6BCECF2A58C719A57AF5E60B9E74FCB31EB1FC130B8BD8DAE6A6A246`

Previous:

- ML-A.1a.1 SHA: `BEB14E77837407BFED7038A6152C7BA11F1D68346117F56B688539A207BAA6AA`
- ML-A.1a SHA: `E13458DE37C5280A8B97EC51ABE1A4D0C85420A1A50777453A5CD21CD99CC569`
- ML-A.1 SHA: `0743C25CEED236E38C9400DAB3FDD0910D469F4BD77743CAC82629947A694BFE`

Owner visual QA is **required** after ML-A.1a.2 packaging. Full pytest remains deferred until after visual QA and before commit/push.

## ML-A.1a.2 owner finding addressed

After freeze success, progress bar must be **100%** (not stuck at 66%). Cancel disabled on success; cancel/fail never show success@100%.

## ML-A.1a.1 owner finding addressed

Acquisition date projection for `Am_all_2014-10-15.mat`:

- Date must be `2014-10-15`, not frame times `04:59`…
- `unique_source_dates` must be **1** for 13 same-date frames
- Legacy invalid frozen audits warn and offer a corrected revision (parent unchanged)
- Task contract selector is clearly labelled on Selection and Freeze
- Gate blocker B is not auto-suggested without missing-data / contract evidence

## Technical Details checks (packaged)

- Phase: `ML-A.1a.1`
- ML dataset readiness protocol: `iml-ml-dataset-readiness-0.1.0`
- Disagreement analysis protocol: `iml-disagreement-analysis-0.1.0`

## Visual / workflow checks (ML-A.1a.1)

Use source `Am_all_2014-10-15.mat`, 13 frames, times 04:59–06:59, one acquisition date, one sequence.

1. Freeze a **new** readiness audit.
2. Overview shows `unique_source_dates = 1` (localized label).
3. Sources/Dates Acquisition Date column shows `2014-10-15`.
4. Frame times remain in the Time column only.
5. Export shows one acquisition date.
6. Close/reopen — saved audit restores its task contract.
7. Open a **legacy** invalid audit (if present) — warning appears; inventory unchanged.
8. Create corrected revision — new audit has valid date; parent unchanged.
9. Export does not create a duplicate audit.
10. RU/EN switching works.
11. No Not Responding / lingering QThread.

## Scientific honesty

- Parameter-scaling contract reports unsupported without parameter labels.
- Candidate morphology never appears in expert target distributions.
- Holdout remains a feasibility assessment, not a completed holdout dataset.
- Do not treat the readiness report as ground truth or scientific validation.
