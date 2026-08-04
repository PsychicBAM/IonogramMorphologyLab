# PHASE 4C.1e.1 Acceptance Report

**Phase:** Verification Failure Repair, Layout-State Migration, Build Identity, and Owner Packaging Readiness  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Diagnostics layout schema:** `2`  
**Sequence-state contract:** `1`  
**Mode:** shadow-only  
**Date:** 2026-08-04  

## Why old EXE QA was invalid for 4C.1e

The owner opened EXE SHA-256:

`CE301D426F71605DEEAA91B4E8B0AB30E8C4EAD6759B1FA0DB6AB7F00675D674`

That binary is the **accepted Phase 4C.1d** package. Phase 4C.1e explicitly did not build a new EXE and did not compute a new SHA. Observations from that EXE (old Layers collapse default, old Features toolbar, missing More / shortcut Help / Ctrl+Shift behaviour, older sequence messages) describe **4C.1d**, not the 4C.1e source tree.

## Source integration issues found

| Area | Finding | Correction |
|---|---|---|
| Persisted layout | 4C.1d saved `feature_diagnostics` sizes with Layers≈0; restore overrode new defaults | `fd_layout_schema_version=2` one-shot migration to ~15/55/30 + Layers open |
| Layers authority | Drawer toggle + zero-width splitter competed | Single left splitter pane; collapse hides panel content but restores width; open default after migrate/Ctrl+0 |
| Shortcuts | QShortcut locals only; Escape not stored | Persistent `self._sc_*` with `WidgetWithChildrenShortcut`; detach window `_esc_shortcut` |
| Help | Drawer used `format_shortcuts_help`; full Help topic needed discoverability | `help/content.py` bodies + `HELP_SYNONYMS` for «Быстрые команды» / Keyboard shortcuts |
| Sequence catalog | Pending vs running messages overlapped; control fall-through | Explicit per-state messages + `_CONTROLS` + import-time catalog assert |
| Build Identity | Next EXE indistinguishable from 4C.1d | Phase `4C.1e.1`, layout schema, sequence-state contract, candidate schemas in identity |
| Tests | Deferred QTimer race; `get_i18n` misuse; weak shadow assert | Deterministic `_restore_layout_and_layers()`; `set_language`; hardened assertions |

No scientific thresholds, V2 geometry, morphology rules, evidence rules, or RuleEngine wiring were changed.

## Import / signal corrections

- `sequence_frame_state.py`: no Qt; no circular import with the page; catalog validated at import  
- `frame_done = Signal(dict)` unchanged in contract; emits include `request_generation_id` / source identity; late generations discarded by page guards  
- Worker test doubles remain compatible (extra signal is additive)

## Layout settings schema migration

- Constant: `FD_LAYOUT_SCHEMA_VERSION = 2`  
- On restore: if stored schema &lt; 2 → apply preferred defaults once, set Layers open, drop obsolete splitter blobs, persist schema 2  
- After migration, user custom sizes persist normally  
- Ctrl+0 always restores preferred ratios + Layers open + balanced mid/Features splitters without clearing V2/candidate/reviews/caches/source  

## Authoritative Layers-pane structure

Horizontal splitter panes:

1. **Layers** (min width 140) — checkboxes, Default layers, Hide overlays  
2. **Canvas + sequence**  
3. **Inspector**  

Open/closed state: `fd_layers_drawer_open` + `layers_panel` visibility inside the left pane (not a floating under-canvas drawer).

## Features toolbar wiring

Single lazy Features toolbar in `_ensure_features_tab`:

- filter + search + short Open + **⋯** More  
- Secondary/technical actions only in the overflow menu  
- Narrow inspector may hide Open; More remains  

## Shortcut registration

| Shortcut | Persistent attribute | Action |
|---|---|---|
| Ctrl+Shift+F | `_sc_detach_features` | Features detach |
| Ctrl+Shift+R | `_sc_detach_sequence` | Sequence results detach |
| Ctrl+0 | `_sc_reset_layout` | Reset Diagnostics layout |
| Escape | `DetachableTableWindow._esc_shortcut` | Close focused detached window |

Context: `WidgetWithChildrenShortcut` on the Diagnostics page so table/search focus does not swallow the shortcuts.

## Help-topic integration

- In-page Help drawer: `format_shortcuts_help` under **Быстрые команды** / **Keyboard shortcuts**; ⌨ opens it  
- Full Help section `feature_diagnostics` lists the same shortcuts  
- Synonyms route shortcut queries to that topic  

## Sequence-state wiring

`resolve_sequence_frame_state` → `_refresh_sequence_frame_state` → morphology panel text + button enablement.  
`frame_done` hydrates the **current** frame only; other frames update sequence rows only; cancelled/stale generations discarded.

## Validator consistency corrections

- No weakening of scientific validators  
- Docs: clarified that 4C.1e did not ship an EXE; added owner verification doc  
- Build Identity / help content aligned with versions (no fake “tests passed” claims)  
- Suspected owner FAIL cluster after 4C.1e is consistent with (a) verifying the wrong EXE and/or (b) layout-restore + test races; repairs target those integration defects  

## Tests changed

`tests/test_phase4c1e_layout_sequence_state.py` — rewritten for:

- catalog completeness  
- schema migration  
- persistent shortcuts  
- Help content/search  
- Build Identity phase `4C.1e.1`  
- deterministic layout restore without timing sleeps  

## Files changed

| Path |
|---|
| `src/ionogram_morphology_lab/ui/sequence_frame_state.py` |
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/detachable_table_window.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `src/ionogram_morphology_lab/ui/v2_diagnostics_worker.py` *(unchanged this sub-phase; contract audited)* |
| `src/ionogram_morphology_lab/help/content.py` |
| `tests/test_phase4c1e_layout_sequence_state.py` |
| `docs/PHASE4C1E_ACCEPTANCE_REPORT.md` *(clarification note)* |
| `docs/PHASE4C1E1_OWNER_VERIFICATION.md` *(new)* |
| `docs/PHASE4C1E1_ACCEPTANCE_REPORT.md` *(this file)* |

## Verification / packaging status (this session)

- **Verification commands were not run** (pytest, validators, linters, type checks)  
- **No EXE was built**  
- **No SHA was calculated**  
- **No commit / no push**  
- **Phase 4C.2 not started**  
- **Production RuleEngine remains unwired**  

This report does **not** claim that tests passed, validators passed, or packaged QA passed.

## Scientific non-claims

- No change to Feature Pipeline V2 science or thresholds  
- No change to morphology-candidate numerical rules or evidence decision rules  
- No change to cache scientific identity semantics  
- No change to geometry/morphology review scientific meaning  

## Remaining owner verification steps

1. Run commands in `docs/PHASE4C1E1_OWNER_VERIFICATION.md`  
2. On green source verification, build portable EXE  
3. Confirm Build Identity phase `4C.1e.1` and a **new** SHA ≠ `CE301D…`  
4. Perform packaged UI QA on that **new** EXE only  
