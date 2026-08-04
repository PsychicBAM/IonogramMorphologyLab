# Phase 4B.2d — Active Source UX, Compatible MAT Selection, Guided Feature Diagnostics Visualization

**Status:** implementation complete (UX / runtime only)  
**Date:** 2026-08-03  
**Feature version preserved:** `iml2-0.2.0`  
**Constraints honored:** no V2 geometry/threshold/registry changes; RuleEngine unchanged; V2 shadow-only; Phase 4C not started; no commit/push.

## Source-card theme root cause

`ActiveSourceCard` used a hard-coded light stylesheet (`background:#f7f7f4`) while labels/buttons inherited dark-theme palette text (near-white). Result: pale/white card with white text and unreadable controls in the packaged dark theme.

**Fix:** `ui/theme.py` theme tokens + `apply_app_theme()`; cards/rows use theme-aware QSS (no hard-coded white card fill). Settings `general.theme` (`system`/`light`/`dark`) is applied at startup and on save.

## Source action names and semantics

| Action | RU | EN | Meaning |
|--------|----|----|---------|
| Unset | Снять как активный | Unset as Active | Clears active session source; inventory kept; file on disk kept |
| Remove | Убрать из проекта | Remove from Project | Removes inventory entry only; never deletes physical MAT |
| Set active | Сделать активным | Set as Active | Reactivates a compatible inventory MAT without reimport |
| Pick | Выбрать активный файл из проекта | Choose active file from project | Selector of compatible inventory files |

Lifecycle is reversible: Active → Unset → Set as Active (no restart / reimport).

## Compatible / incompatible activation policy

`ui/source_roles.py` classifies each MAT:

- `primary_ionogram_source` — has supported `Amp_all`, frame extractable → may activate
- `auxiliary_archive_product` / `unsupported` — e.g. `ALL_data` without `Amp_all` → inventory only
- `missing` — path unavailable

Import with `make_active=True` activates **only** when classification allows. A valid `Am_all` active source is never replaced by incompatible `ALL_data`. User sees localized explanation + “Choose a suitable Am_all file”.

## Imported-file row actions

`ui/import_file_list.py` replaces text-only import cards with per-file rows:

- filename, product, variables, shape, status, badge, technical details
- actions: Set as Active / Unset as Active / Open / Remove from Project / Open Folder / Technical Details
- badges: Active / Inactive / Auxiliary / Incompatible / Unavailable

## Feature Diagnostics visualization

- Raw frame loads automatically before V2 (`frame_ready` state)
- After V2: raw remains under overlays; default layers = raw, accepted trace, interference, centerline, branch labels
- Aspect-preserving Fit / 100% / zoom ± / reset; open in Viewer; sync frame
- Explicit run states (no blank black panel as an implicit state)
- Human-readable summary panel («Что сделала диагностика») — diagnostic only, no morphology
- Grouped localized feature list; technical IDs behind toggle
- Layer legend, tooltips, default/hide-overlay controls
- Viewer/Diagnostics identity: MAT, source SHA, frame, time, profile, contract, raw frame SHA
- Mismatch clears stale overlays

## MAT A → MAT B / Remove evidence (automated)

Covered in `tests/test_phase4b2d_active_source_ux.py`:

- A active → import incompatible B → A remains active
- Activate B → A inactive, diagnostics cleared, B raw frame loads
- Remove from project → inventory gone, physical file remains
- Unset → Set as Active without reimport
- Cancel switch confirmation keeps A
- RU/EN labels and missing-`Amp_all` user messages

## Manual packaged-EXE QA

Manual dark/light + scale screenshots are recommended on the rebuilt portable EXE (checklist in phase brief §14). Automated suite covers functional behavior; visual QA of theme contrast at 100/125/150% should be confirmed on target displays (1366×768 / 1920×1080).

## Tests / validators

- Phase 4B.2c + 4B.2d UI tests: **42 passed**
- Full repository suite: **269 passed**
- Validators: shadow mode OK; registry 93; synthetic geometry 17/17 `iml2-0.2.0`; i18n OK

## Packaged EXE SHA-256

`6C1C37324374F64544A0DC5029EF30200CA0FFFD2C7A760FD29F038EB0A04DB5`

Path: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Explicit non-claims

- No scientific validation claimed
- No morphology accuracy improvement claimed
- Feature Pipeline V2 measurements/thresholds unchanged
- V2 not enabled by default
