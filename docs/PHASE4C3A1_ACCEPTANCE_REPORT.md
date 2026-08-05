# Phase 4C.3a.1 — Acceptance Report

**Build Identity:** `4C.3a.1`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.3a):** `5E2F594B1BE173F9179C62F577C0C7C3CA23B6C42485A8131CD36FD3E4DFB48D`  
**New EXE SHA-256:** `A5CA0222A03406F15FBF75BBF77422AD5D988763540ADC5FCAD0F39D1ED9C061`

**Verification mode:** time-constrained targeted verification.  
**Full pytest suite deferred** until the final release gate before commit/push.  
Owner visual QA is **not** claimed PASS.

---

## Owner screenshot findings

1. Project open; active source `2014-10-15` visible elsewhere.  
2. Campaign page showed the active source.  
3. Wizard Step 2 “Sources and dates” showed **no visible inventory rows**.  
4. Active source was not selected.  
5. Raw code `no_sources_selected` appeared in the status area.  
6. Pale / nearly invisible text on a white/light wizard background.  
7. Next appeared usable despite empty selection.  
8. Campaign list/dashboard mixed EN state tokens (`ready`, `Pilot campaign (ready)`).

---

## Exact inventory-population root cause

`list_registered_project_sources()` enumerated only `project.source_paths` and inserted the active source **only when** `auth.source_sha256` was already non-empty.

Owner-like failure mode (reproduced):

- live inventory lived in `session.selected_mats`;
- `project.source_paths` could be empty / out of sync;
- Campaign page active-source label does **not** require SHA;
- wizard therefore received **zero rows**, validation emitted `no_sources_selected`, and nothing was auto-checked.

Not a first-MAT fallback issue. Not an identity-gate bypass. Rows were not merely “styled invisible” in the empty case (though contrast independently hid content when rows did exist under Aero).

**Fix:** union `project.source_paths` + `session.selected_mats` + active MAT; always list the active source; compute/cached SHA for active when opening the wizard; refresh on `inventory_changed` / `active_mat_changed` / sources-page `initializePage`.

---

## Contrast root cause

Hardcoded dark-theme QSS (`color: #f0f0f0`) was applied while Windows `QWizard` Aero/native chrome kept a **light/white** page background, producing pale text on white.

**Fix:** `QWizard.ClassicStyle` + theme tokens from `source_card_tokens()` / `resolve_theme_name()` so background and foreground always pair for dark and light modes.

---

## Source-table behaviour

- Minimum height ≥ 220 px; font-metric column widths; stretch on source name.  
- Columns: Use / Source / Date / State / short SHA / coverage.  
- Active available source checked by default.  
- Multi-select via checkboxes; preserve checks across inventory refresh.  
- No editable SHA field.

---

## Empty-state localization

Never show raw `no_sources_selected`. Localized states for loading / no registered sources / none selected / load failure, with Retry / Close wizard. Technical errors only in expandable Technical Details.

---

## Next-button gating

Sources page `isComplete()` requires at least one validated available inventory source (inventory ID + authoritative SHA). Next stays disabled until then; blocker label shows the localized reason.

---

## Mixed-language campaign-state closure

UI maps `ready→Готова`, `draft→Черновик`, `active→Активна`, `paused→Приостановлена`, `completed→Завершена`, `archived→Архивная`. User-entered names (e.g. “Pilot campaign”) remain unchanged. Canonical codes remain in storage / tooltips / Technical Details.

---

## Invalid legacy campaign

Repair Source Mapping / archive remain. New wizard creates a separate valid campaign from real inventory. Frozen invalid cohort is not mutated.

---

## Focused tests

| Suite | Result |
|-------|--------|
| `test_phase4c3a1_wizard_inventory.py` | **9 passed** |
| Warning audit (`-W default` on 4C.3a.1) | No new ResourceWarnings (only env pytest-asyncio deprecation) |
| `test_phase4c3a_*` + 4C.3a.1 | **19 passed** |
| Campaign + active-source high-risk set | **30 passed** |

**Full pytest:** deferred.

---

## Validators

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature / candidate shadows | OK |
| Corpus / campaign validators | OK |
| i18n | OK (782/782 keys) |
| docs | passed |
| hygiene | 0 violations |

---

## Build

- Build Identity: `4C.3a.1`  
- Scientific versions unchanged; shadow-only  
- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
- SHA-256: see header (must ≠ 4C.3a)

---

## Packaged / domain smoke

Synthetic two-MAT project with `source_paths=[]` desync + active B:

1. Inventory lists A+B; B active with SHA  
2. Campaign create uses real registered identity  
3. Invalid legacy “abdalla” campaign remains separate  

Owner visual QA of the packaged dark-theme wizard remains required.

---

## Explicit deferral

**Targeted verification passed; full-suite regression is deferred due to the owner’s time-constrained development window.**

Full `python -m pytest` remains mandatory before commit/push.

---

## Git

- **No commit**  
- **No push**  
- Staged: 0  
