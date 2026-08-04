# PHASE 4C.1e.2 Acceptance Report

**Phase:** Sequence Frame Follow UX, Per-Frame Feature Hydration, and Shortcut Button Clarity  
**Prior accepted EXE SHA-256 (4C.1e.1):**  
`DBE5879ECFD8ABEBEB2CCDF1B7EABB4274E9AEFA046A02C4C5BFA530FA0225A8`  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.2`  
**Mode:** shadow-only  
**Date:** 2026-08-04  

## Owner finding

Packaged QA of 4C.1e.1 confirmed layout, Help, More menu, detach, RU/EN, Cancel, and identity. Remaining issues:

1. Features table for the displayed frame could stay empty during Sequence V2.
2. Status stayed generic (“Feature Pipeline V2 is running”).
3. It was unclear that selecting a sequence row hydrates full Features/candidate.
4. Current frame could sit outside the selected sequence with no explanation.
5. Compact shortcut control near Reset layout was visually unclear.

## Features is single-frame; sequence table is multi-frame

The embedded Features inspector always represents **exactly one active frame**.  
The sequence results table holds **summary + identity** for many frames.

Selecting a completed row hydrates that frame into the single-frame inspector (ionogram, layers, Summary, Features, provisional morphology, Evidence/Review identity, Technical details). Features from different frames are never mixed in the table model.

## Follow processing behaviour

Visible option: **«Следовать за обработкой»** / **“Follow processing”**.

- Default: enabled when a new sequence starts.
- On `frame_done` with Follow on: select the completed row, update frame/time, hydrate V2 result into Features, hydrate/evaluate candidate per existing contract (no duplicate calc when cached), update Summary/morphology, scroll the table.
- Does not rerun V2.

## Manual selection behaviour

Manual row click, frame number entry, Previous/Next, or leaving the selected sequence disables Follow and shows:

- RU: «Автоматическое следование приостановлено: выбран кадр вручную.»
- EN: “Automatic follow paused: a frame was selected manually.”

**Resume follow** / **«Возобновить следование»** re-selects the latest completed frame and resumes `frame_done` follow.

## Current frame outside the selected sequence

If the displayed frame is not in the selected sequence:

- Features empty state explains the mismatch (RU/EN).
- Compact status + actions: Latest frame, Resume follow, Show results table.
- Sequence start corrects an outside current frame by selecting the first sequence frame and enabling Follow.

## Features empty states

Localized empty states cover: pending V2, outside sequence, hydrating, legacy/incomplete, failed, and no applicable scientific features. The Features table is never left blank without explanation.

## `frame_done` hydration

Guards: source SHA, request generation, frame index. Updates the sequence row. Follow-on hydrates inspector; Follow-off updates the row only (manual selection preserved). Older generations discarded. Cancel path remains non-blocking.

## Candidate control states

Enablement follows the **selected frame’s** sequence-state contract (pending / V2 ready / cached candidate / running), not only a global sequence-running flag. Automatic evaluation avoids duplicate calculation when a valid candidate already exists.

## Shortcut button replacement

Unclear glyph replaced with readable **«Команды»** / **“Shortcuts”** (tooltip + accessible name). At very narrow widths: standard Qt Help icon, same accessible name/tooltip. Opens existing shortcut Help subsection, which now explains Follow / pause / resume / per-frame Features.

## Files changed

| Path |
|---|
| `src/ionogram_morphology_lab/ui/sequence_frame_state.py` |
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/detachable_table_window.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `src/ionogram_morphology_lab/help/content.py` |
| `tests/test_phase4c1e_layout_sequence_state.py` *(follow pause guard + Build Identity phase)* |
| `tests/test_phase4c1e2_sequence_follow.py` *(new)* |
| `docs/PHASE4C1E2_ACCEPTANCE_REPORT.md` *(this file)* |

## Tests added but not run

`tests/test_phase4c1e2_sequence_follow.py` covers:

- sequence starts on first selected frame when current is outside
- Follow enabled by default
- `frame_done` selects latest when Follow on
- manual row selection disables Follow
- Resume selects latest completed
- other-frame result does not overwrite manual selection
- Features empty pending / outside
- completed row hydrates Features and candidate cache
- pending row does not rerun V2
- failed row shows failure reason
- sequence completion clears running message
- Features identity line per selected row
- shortcut control readable text / accessibility
- shortcut Help explains per-frame Features
- old generation discarded
- Cancel remains safe
- production RuleEngine unchanged
- shadow-only contracts unchanged

**This session did not execute pytest, validators, linters, builds, packaging, or SHA commands.**

## Explicit no-build / no-SHA statement

- No EXE was built in this session.
- No SHA-256 was calculated for a new package.
- Owner verification and packaging remain manual.

## Scientific non-claims

This phase does **not** claim:

- changes to Feature Pipeline V2 calculations, geometry algorithms, or thresholds
- changes to morphology candidate rules/thresholds or cache identity
- changes to evidence rules, review semantics, or production RuleEngine
- scientific validation or production enablement
- that tests or validators passed

## Remaining owner verification steps

1. Start a six-frame sequence while the current frame is outside it → UI selects first sequence frame; Follow on.
2. Each completed frame auto-shows ionogram, Features, and candidate when Follow is on.
3. Manual row selection pauses Follow; Resume returns to latest completed.
4. Selecting any completed row shows that frame’s detailed Features.
5. Pending rows show a clear pending message.
6. Sequence completion removes the perpetual running message.
7. Shortcut control reads Commands/Shortcuts; Help lists sequence Follow behaviour.
8. RU/EN correct; Cancel stable; no Windows Not Responding.
9. Build Identity shows phase `4C.1e.2` after owner packaging.

Do not begin Phase 4C.2 until owner accepts this UX follow-up.
