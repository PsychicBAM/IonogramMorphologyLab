# Packaged UI Manual QA — v1.1.1 (Phase 3C)

Evidence captures (live MainWindow, Segoe UI, Windows platform) are stored under:

`docs/assets/screenshots/v1.1.1/manual_qa/`

Index: `docs/assets/screenshots/v1.1.1/manual_qa/CAPTURE_INDEX.md`

Packaged EXE (rebuild after Phase 3C docs): see SHA-256 at the end of this file after rebuild.

## Resolutions / scales tested

| Resolution | Scale | Capture tag | MATLAB Studio | Projects open controls | Result actions readable | Parameters detail | Help | RU/EN retranslate |
|------------|-------|-------------|---------------|------------------------|-------------------------|-------------------|------|-------------------|
| 1366×768 | 100% | `1366x768_100` | PASS — full «Запустить в MATLAB» / «Проверить код без запуска»; Editor tools menu; vertical result actions | PASS — Open / Choose folder / Open recent visible | PASS — vertical list, no fragment buttons | PASS | PASS | PASS (separate `_en` / `_ru` grabs) |
| 1366×768 | 125% | `1366x768_125` | PASS — primary actions remain full-width; library uses «Ещё…» | PASS — Current project card + Open section; Create header may require scroll | PASS | PASS | PASS | PASS |
| 1366×768 | 150% | `1366x768_150` | PASS with scroll — editor remains central; no page-level horizontal scroll | PASS with vertical scroll on Projects | PASS | PASS | PASS — topic body may need scroll | PASS |
| 1920×1080 | 100% | `1920x1080_100` | PASS — more result tabs visible before scroll buttons | PASS — Create section more visible | PASS | PASS | PASS | PASS |

## Checklist notes

### Clipped action buttons
- **Pass:** Primary MATLAB actions are full-width vertical buttons; secondary editor and library actions use menus («Инструменты редактора…», «Ещё…», «Дополнительно…») with full labels in the menu.
- **Intentional elision:** MATLAB result tabs may show scroll arrows at 1366×768; full tab titles are set as **tooltips** via `set_tab_labels()`.

### Projects
- Current project card shows name, path, created, active source, active run, unsaved-change warning.
- Open Project / Choose Project Folder / Open Recent Project buttons visible.
- Recent list includes Open and Remove («Убрать»).

### MATLAB Values / Figures / Files (runtime evidence)
- Representative R2019a runs (see `MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.md` + `workspaces/_phase3c_matlab_runtime/`):
  - Values / registered features confirmed for trace, interference, branch, Spread-F, layer, parameter-only methods.
  - PNG figure confirmed for `iml_render_raw_ionogram` (not claimed for all 32 declared figure methods).
  - Parameter-only `iml_estimate_foF2_candidate` produced no image and Expected Method Output explains that.
  - No-output scientific status `completed_with_no_registered_output` verified for empty-output contract.
  - Source MAT SHA-256 unchanged across runs.

### Language switch
- Separate EN/RU captures for each case confirm active-page retranslation of ordinary UI strings.
- Canonical technical tokens / MATLAB identifiers may remain English.

## Failures / follow-ups
- None blocking for Phase 3C documentation acceptance.
- Create-project fields may sit below the fold at 125–150% — vertical scroll required (not horizontal).

## SHA-256

Portable EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

**SHA-256:** `A9A5BAA1C54E67B7C887DA7CF1ABF8DAED121533F2F7C9E05EE50C608466D61D`
