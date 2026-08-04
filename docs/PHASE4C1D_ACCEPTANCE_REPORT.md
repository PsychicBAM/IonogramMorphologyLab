# PHASE 4C.1d Acceptance Report

**Phase:** Resizable Diagnostics Workspace, Detachable Feature and Sequence Tables, Low-Height Scrolling, and Final UI Polish  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Mode:** shadow-only — **UI/UX only**  
**Date:** 2026-08-04  
**Prior EXE (owner-tested 4C.1c):** `3A6A80405BB7C98EE22E33E4E581175AC6ADE089BC7ED225B291AD5120A24ED7`

## Verdict

Diagnostics layout is now user-resizable with a persistent horizontal canvas/inspector splitter, a sequence vertical splitter that keeps results reachable, detachable Features and Sequence windows sharing models/data, an outer scroll area for low-height windows, and RU/EN localization for Close and new layout actions. No scientific thresholds, cache identity, or RuleEngine wiring changed.

## Splitter architecture

| Splitter | Role | Default |
|---|---|---|
| `self.split` (H) | layers \| canvas+seq \| inspector | ~65% canvas / ~35% inspector |
| `self._mid_vsplit` (V) | ionogram \| sequence results | ~65% / ~35% in sequence mode |
| `self._features_splitter` (V) | feature table \| explanation | ~70% / ~30% |

- Dragging persists via `general.splitter_states` / `ux.fd_features_splitter`
- Frame/tab/language switch does not force-reset sizes
- **Reset layout** (`Ctrl+0`) restores defaults without V2/candidate I/O
- Inspector no longer capped at 520 px max width

## Persisted layout state

- Main H-splitter: `feature_diagnostics`
- Mid V-splitter: `feature_diagnostics_mid_v`
- Features internal: `fd_features_splitter`
- Detached window geometry: `fd_detach_features_geometry`, `fd_detach_sequence_geometry`

## Features pop-out

- Action: **Open table in separate window** / **Открыть таблицу отдельно** (`Ctrl+Shift+F`)
- Non-modal `DetachableTableWindow` sharing `FeaturesTableModel` / proxy
- Search/filter, sorting, explanation panel, pin/follow identity
- Follows active frame by default; pin shows stale banner when frame changes

## Sequence Results pop-out

- Action: **Open results in separate window** / **Открыть результаты отдельно** (`Ctrl+Shift+R`)
- Synced from the same `_sequence_results` list on each fill
- Double-click / Open selected frame → Diagnostics frame
- Fit columns is manual only (no per-row `resizeColumnsToContents`)

## Responsive / scroll strategy

- Outer `QScrollArea` wraps page content (`minimumHeight` ~640) so lower controls remain reachable at 1280×720
- Tables retain internal scrollbars
- Sequence pane gets `minimumHeight` 120 and cannot vanish below the window when visible
- Canvas minimum height lowered to 160 to allow sequence split on short displays

## Detached-window identity

- Features: source SHA, frame, diagnostics id, feature version
- Sequence: source SHA, frame, sequence count / generation
- Source detach closes Features / Sequence / Evidence detach windows
- Late frame updates respect pin/follow flags

## Localization

- New controls RU/EN
- `Close` → **Закрыть** via `localize_dialog_buttons` (Evidence, detach windows, Build Identity)
- Language switch retranslates open detach windows without science refresh

## First/warm timings (unchanged contract)

Features model/view path from 4C.1c retained (no eager 93-row widgets; registry lru-cached). Layout operations perform no MAT / V2 / candidate work.

## Tests and validators

| Check | Result |
|---|---|
| `tests/test_phase4c1d_layout_detach.py` | added |
| Full `pytest tests/` | **442 passed** |
| morphology shadow / V2 shadow / i18n / docs / registry / synthetic geometry | OK |

## Scientific non-claims

- No change to V2 science, morphology thresholds, evidence rules, cache identity, or review semantics  
- Production RuleEngine unwired  
- Phase 4C.2 not started  

## Remaining blockers

- Owner packaged EXE QA checklist (below)  
- Optional: deeper collapse of source/why panels (toolbar actions present; session collapse map started)

## Packaged EXE

| Field | Value |
|---|---|
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| SHA-256 | `CE301D426F71605DEEAA91B4E8B0AB30E8C4EAD6759B1FA0DB6AB7F00675D674` |

### Owner QA checklist

1. Drag canvas/inspector splitter  
2. Sizes survive tab/frame switches  
3. Open Features separately; maximize/resize  
4. Search/filter; pin/unpin; switch frame  
5. Sequence mode; drag ionogram/results splitter  
6. Sequence table always reachable  
7. Open sequence results separately  
8. Resize app to 1280×720; scroll to lower content  
9. RU/EN with detach windows open; Close → Закрыть  
10. Run/Cancel sequence; no Not Responding  

## Git

- **No commit**  
- **No push**  
