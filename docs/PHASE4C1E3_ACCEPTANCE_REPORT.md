# PHASE 4C.1e.3 Acceptance Report

**Phase:** Embedded Sequence Table Readability, Responsive Columns, Palette Integrity, and Final Packaged Closure  
**Prior accepted EXE SHA-256 (4C.1e.2d):**  
`35B5B316E0AFE59F36648B32B349E226DDE184E8787E67F476B490A089F4293C`  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (unchanged)  
**Candidate cache / ledger schema:** `2` / `2` (unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (unchanged)  
**Diagnostics layout schema:** `2` (unchanged)  
**Sequence-state contract:** `1` (unchanged)  
**Build Identity phase:** `4C.1e.3`  
**Mode:** shadow-only  
**Date:** 2026-08-04  
**Commit / push:** none (not performed)

## Owner visual finding

Owner packaged QA of 4C.1e.2d confirmed all functional Sequence Follow / Features / Cancel / RU-EN behaviour. Remaining defect: the **embedded** Sequence Results table was hard to read (compressed columns, clipped values, washed-out cell text). The **detached** table looked normal with the same data.

## Screenshot interpretation

Data existed and was correct. The defect was restricted to embedded presentation: narrow mid-pane + light hard-coded row backgrounds without theme-safe foreground + all 19 columns always visible with no compact profile.

## Exact root cause

Not a disabled-widget / Disabled-palette bug. Audit showed:

- `seq_table.isEnabled()` remained true during and after processing;
- no parent disable of the table;
- no `QGraphicsOpacityEffect`;
- no low-opacity stylesheet on the table.

**Primary contrast defect:** `_style_sequence_table_row` painted light pastel/white `QColor` backgrounds (e.g. `#FFFFFF`, `#F5F5F5`) without setting foreground. Under dark theme, palette text `#e8eaed` on those light cells looked washed / low-contrast. Detached table skipped that styling, so it remained readable.

**Primary width defect:** all 19 model columns were always shown in the narrow embedded pane; resize was Interactive with no compact visibility profile and no font-metric minimum widths. Fit was a manual “Столбцы”/“Fit” action only, never a Columns menu.

## Embedded vs detached

| Aspect | Embedded (before) | Detached (before) |
|---|---|---|
| Widget | `self.seq_table` in mid vertical splitter | Separate `QTableWidget` in `DetachableTableWindow` |
| Viewport | Narrow (~35% of mid pane) | ~900×640 window |
| Row markers | Light hard-coded backgrounds, no FG | No marker styling |
| Columns | All 19 always visible | All 19, more horizontal space |
| Result | Washed text + clipping | Readable |

After 4C.1e.3: same model; view-specific compact/full profiles; theme-safe marker FG/BG on both; detached keeps full profile.

## Enabled / palette audit

- Explicit `_ensure_sequence_table_interactive()` after fill and on worker completion.
- Items keep `ItemIsEnabled | ItemIsSelectable` so Disabled palette never washes rows.
- Marker colours from `marker_colors()` using theme tokens (`source_card_tokens` / dark+light).
- Foreground always high-contrast theme text; backgrounds are subtle navigation markers only.

## Responsive column strategy

One model (`_sequence_row_values`, 19 columns). View profiles:

**Compact (embedded default):**  
frame, time, quality, trace, branches, interference, H, V, assess, candidate, strength.

**Full (detached default / “Show all columns”):** all 19.

Hidden columns remain in the model (exports unchanged). Horizontal scrollbar `AsNeeded`. Widths from `QFontMetrics` via `default_min_widths` / `preferred_widths`. No `ResizeToContents` on every `frame_done`. User widths persisted; Reset restores profile widths.

## Compact / full profiles

- RU «Компактная таблица» / EN “Compact table”
- RU «Полная таблица» / EN “Full table”
- Columns menu: Compact set · Show all columns · Reset column widths · per-column checkboxes
- Essential frame/time cannot be unchecked (Reset / Compact restore them)
- Settings keys: `fd_seq_table_profile`, `fd_seq_hidden_columns`, `fd_seq_column_widths`

## Row markers and contrast

Markers remain UI/navigation only (displayed / processing / last completed / cached / failed). They no longer encode confidence via text brightness. Dark and light themes both keep strong foreground contrast.

## Automatic candidate Sequence-only contract

Unchanged and regression-tested:

- Sequence mode: `_enrich_sequence_morph_candidates` / row hydrate may evaluate on cache miss.
- Single-frame: `_apply_frame_result` → `_try_load_cached_morph` (lookup only); Calculate/Recalculate remain manual.

## Files changed

| Path |
|---|
| `src/ionogram_morphology_lab/ui/sequence_table_presentation.py` *(new)* |
| `src/ionogram_morphology_lab/ui/feature_diagnostics_page.py` |
| `src/ionogram_morphology_lab/ui/build_identity.py` |
| `tests/test_phase4c1e3_sequence_table_readability.py` *(new)* |
| `tests/test_phase4c1e2_sequence_follow.py` *(Build Identity assert → 4C.1e.3)* |
| `tests/test_phase4c1e_layout_sequence_state.py` *(Build Identity assert → 4C.1e.3)* |
| `docs/PHASE4C1E3_ACCEPTANCE_REPORT.md` *(this file)* |

## Focused test results

```text
python -m pytest tests/test_phase4c1e3_sequence_table_readability.py tests/test_phase4c1e2_sequence_follow.py -q
56 passed in 68.81s
```

## Full pytest

```text
python -m pytest tests -q
523 passed in 354.78s (0:05:54)
```

- Failed: **0**
- Errors: **0**
- Warnings: **0**

## Validators

| Command | Result |
|---|---|
| `validate_feature_registry_v2.py` | `OK registry=93 emitted=93 missing=0` |
| `validate_synthetic_geometry_v2.py` | `OK synthetic_geometry 17/17 version=iml2-0.2.0` |
| `validate_feature_shadow_mode.py` | `OK shadow_mode_isolation` |
| `validate_morphology_candidate_shadow.py` | `OK morphology_candidate_shadow` |
| `validate_i18n.py` | `validate_i18n OK` |
| `validate_docs.py` | `Documentation validation passed.` |

## Packaging

```text
powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1
```

Succeeded.

**EXE path:**  
`E:\ionog\conference_presentation\IonogramMorphologyLab\dist\IonogramMorphologyLab\IonogramMorphologyLab.exe`

## Build Identity

| Field | Value |
|---|---|
| Phase | `4C.1e.3` |
| Feature / geometry | `iml2-0.2.0` |
| Candidate engine | `iml-morph-candidate-0.1.1` |
| Candidate cache schema | `2` |
| Evidence ledger schema | `2` |
| Diagnostics layout schema | `2` |
| Sequence-state contract | `1` |
| Mode | shadow-only |

Frozen PYZ `collect_build_identity` const confirmed: `4C.1e.3`.

## SHA-256

```text
F8690809606B013E5A51A52564FBF1A8994FE06C4F1B42AF9DE6A4B65EF03CFE
```

Differs from prior 4C.1e.2d  
`35B5B316E0AFE59F36648B32B349E226DDE184E8787E67F476B490A089F4293C`.

## Packaged smoke QA

| # | Check | Result |
|---|---|---|
| 1 | Application starts / responds | **PASS** — process alive, `Responding=True` |
| 2 | Build Identity `4C.1e.3` | **PASS** — frozen bytecode |
| 3 | `--smoke-test` | **PASS** |
| 4 | V2 worker child can spawn | **PASS** |
| 5–17 | Embedded readable table, enabled state, widths, H-scroll, detach, Columns menu, Follow/manual/resume, Sequence auto-candidate, single-frame manual candidate, Cancel | **PASS (contract)** via `test_phase4c1e3_sequence_table_readability.py` + follow suite |
| 18 | No Not Responding on launch | **PASS** |

### Visual checks still requiring owner confirmation

Live desktop click-through of this EXE in an interactive session (agent session has `MainWindowHandle=0`):

- Embedded table text contrast under dark/light themes with real sequence data;
- Horizontal scrollbar feel in a narrow Diagnostics pane;
- Columns menu glyphs / RU-EN labels in the live window;
- Detached “Full table” side-by-side visual parity.

Widget tests cover the same contracts; visual PASS on the packaged screenshot is for the owner.

## Scientific non-claims

- No Feature Pipeline V2 calculation changes.
- No geometry / candidate rule or threshold changes.
- No evidence decision-rule changes.
- No automatic candidate behaviour change in single-frame mode.
- No production RuleEngine enablement.
- No Phase 4C.2 work started.

## Git

- **No commit**
- **No push**
