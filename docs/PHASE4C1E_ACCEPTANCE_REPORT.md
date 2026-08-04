# PHASE 4C.1e Acceptance Report

**Phase:** Diagnostics Layout Defaults, Compact Feature Actions, Shortcut Help, and Sequence-to-Morphology State Synchronization  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Mode:** shadow-only — **UI/UX and state-clarity only**  
**Date:** 2026-08-04  
**Prior accepted EXE (4C.1d):** `CE301D426F71605DEEAA91B4E8B0AB30E8C4EAD6759B1FA0DB6AB7F00675D674`

> **Packaging note:** Phase 4C.1e did **not** build a new EXE. Screenshots or QA against SHA `CE301D…` exercise the **previous 4C.1d binary**, not this source tree. See `docs/PHASE4C1E1_OWNER_VERIFICATION.md` and `docs/PHASE4C1E1_ACCEPTANCE_REPORT.md` for repair/migration follow-up.

## Verdict

Preferred Diagnostics defaults now keep **Layers left / ionogram center / inspector right**, Features actions use a compact primary bar with a **More…** overflow, Help documents **Keyboard shortcuts / Быстрые команды**, and Sequence mode exposes an explicit **current-frame V2/candidate state** so the morphology panel no longer looks like a generic “not calculated” idle state while a sequence is running.

## Preferred default layout

| Pane | Role | Default share |
|---|---|---|
| Left | Layers (checkboxes, Default layers, Hide overlays) | ~15% (`150`) |
| Center | Display toolbar, ionogram, sequence results (vertical split) | ~55% (`550`) |
| Right | Summary / Features / Provisional morphology / Geometry / Technical | ~30% (`300`) |

- Layers pane minimum width 140; not collapsed by default  
- `Ctrl+0` / **Reset** restores preferred ratios and expands Layers  
- Custom splitter positions still persist after the user changes them  
- Entering/leaving sequence mode does not reset horizontal sizes  

## Layers visibility

- Default: Layers drawer **open** (`fd_layers_drawer_open` default `True`)  
- Layers remain a real left splitter pane (not under/behind the ionogram)  
- Collapse still available via the Layers toggle; session remembers state  

## Features overflow design

Visible primary controls:

- category filter  
- search  
- short **Open** / **Отдельно** (full text in tooltip)  
- **⋯** More menu  

Overflow actions (RU/EN):

- Open table in separate window / Открыть таблицу отдельно  
- Expand table / Развернуть таблицу  
- Collapse explanation / Свернуть объяснение  
- Reset feature layout / Сбросить расположение признаков  
- Show technical IDs / Показать технические ID  
- Copy selected feature / Скопировать выбранный признак  
- Export features / Экспортировать признаки  

At narrow inspector widths, the Open button may hide; the action remains in More…

## Help shortcut list

Help drawer subsection **Keyboard shortcuts** / **Быстрые команды**, plus compact **⌨** next to Reset layout.

Documented registered shortcuts:

| Shortcut | EN | RU |
|---|---|---|
| Ctrl+0 | Reset Diagnostics layout | Сбросить расположение Diagnostics |
| Ctrl+Shift+F | Open Features table in a separate window | Открыть таблицу признаков отдельно |
| Ctrl+Shift+R | Open Sequence Results in a separate window | Открыть результаты последовательности отдельно |
| Escape | Close the active detached window | Закрыть активное отдельное окно |

Also explained: Follow/Pin, horizontal splitter, sequence vertical splitter, outer scrolling, detachable tables. Full Help topic `feature_diagnostics` updated accordingly.

## Sequence / candidate state model

Module: `ui/sequence_frame_state.py`

States for the **currently displayed frame**:

- `sequence_not_started`  
- `sequence_v2_pending`  
- `sequence_v2_running_current_frame`  
- `sequence_v2_ready_candidate_pending`  
- `sequence_candidate_running`  
- `sequence_candidate_ready`  
- `sequence_candidate_cached`  
- `sequence_frame_not_yet_processed`  
- `sequence_frame_failed`  
- `sequence_cancelled`  
- `sequence_result_stale`  

Misleading idle copy such as bare “V2 not calculated / candidate not calculated” is replaced by these messages while sequence work explains the real situation.

## Current-frame synchronization

- `V2DiagnosticsWorker.frame_done` emits each completed frame  
- If the completed frame equals the displayed frame: hydrate V2, resolve/evaluate candidate per existing sequence contract, update morphology panel and sequence row  
- Other-frame callbacks update the table only and cannot overwrite the current morph panel  
- Cancelled / wrong generation / wrong source SHA callbacks are discarded  
- Selecting a sequence row loads that frame’s V2 + candidate with identity checks  
- Candidate Calculate/Recalculate/Evidence/Review enablement follows **current-frame** state, not a blanket Sequence-mode disable  

## Identity guards

Unchanged and still enforced:

- source SHA  
- frame index  
- diagnostics cache ID / feature version (via existing apply/hydrate paths)  
- candidate result identity for Evidence/Review  
- sequence `request_generation_id`  

## Responsive sequence table behaviour

- Sequence mode always shows the results pane (empty until rows arrive)  
- Minimum table height preserved; vertical splitter can enlarge results  
- **Show results table** / **Показать таблицу результатов** scrolls/expands to the pane  
- Outer page scroll retained for 1280×720 reachability  
- Detachable results action unchanged  

## Files changed

| Path | Change |
|---|---|
| `src/.../ui/feature_diagnostics_page.py` | Preferred 3-pane defaults; Features overflow; shortcuts Help; sequence sync/UI |
| `src/.../ui/sequence_frame_state.py` | **New** — state model, messages, shortcut help text, control enablement |
| `src/.../ui/v2_diagnostics_worker.py` | `frame_done` signal for progressive sequence sync |
| `src/.../help/content.py` | Feature Diagnostics layout/shortcut documentation |
| `tests/test_phase4c1e_layout_sequence_state.py` | **New** — tests listed below (not executed in this session) |
| `docs/PHASE4C1E_ACCEPTANCE_REPORT.md` | This report |

## Tests added but not run

`tests/test_phase4c1e_layout_sequence_state.py` covers:

- preferred default Layers visibility  
- Ctrl+0 ratio restore  
- three-pane persistence  
- narrow Features toolbar labels / More menu  
- RU/EN shortcut Help  
- registered vs documented shortcuts  
- sequence pending / not-yet-processed messages  
- candidate control enablement when V2 ready  
- other-frame / cancelled-generation callback isolation  
- sequence row candidate hydration  
- Show results table / 1280×720 reachability  
- language retranslation of sequence status  
- no science from layout/help actions  
- RuleEngine untouched / shadow-only markers  

## Verification commands

**No verification commands were run in this implementation session.**  
Per owner instruction: no pytest, validators, linters, type checks, packaging, or EXE build.  
No SHA was calculated. The owner will run verification and packaging manually.

## Scientific non-claims

- No change to Feature Pipeline V2 science, geometry thresholds, morphology-candidate rules/thresholds, cache scientific identity, evidence rules, or review semantics  
- Production RuleEngine unwired / unchanged  
- Phase 4C.2 not started  
- No commit / no push  

## Remaining blockers

- Owner manual QA of the checklist in the phase brief (default layout, overflow, Help shortcuts, sequence state clarity, Cancel, no Not Responding)  
- Owner to run pytest / validators / portable packaging as desired  
