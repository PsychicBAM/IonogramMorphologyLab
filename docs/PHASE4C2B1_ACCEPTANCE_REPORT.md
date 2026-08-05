# Phase 4C.2b.1 — Acceptance Report

**Build Identity:** `4C.2b.1`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2b):** `55788895CAA9D28CE65768BC238DC50DFC112FE483E0F1698413845EE29F23B0`  
**New EXE SHA-256:** `D97A54914F1B71E4C1AEFE900F624C64433A0AB2E3C0AB3DB90112223E7BC609`  

Owner visual QA is **not** claimed PASS. This phase is a narrow visual/usability closure.

---

## Owner visual findings (4C.2b)

Accepted scientific/workflow behaviour from 4C.2b remains in force. Remaining failures were visual/usability only:

1. Guided Review opened to a nearly empty large panel — next action unclear.
2. Rapid Review collapsed the ionogram and comment editors at some window sizes.
3. Structured Comment Builder was one long flat checklist.
4. Corpus toolbar still truncated long actions despite overflow.
5. Layout failed at the owner’s real window size / interface scale.

---

## Root causes

| Symptom | Root cause |
|---------|------------|
| Guided blank panel | Guided tab only showed a bare label + button; empty/no-cohort path cleared text; no stage card, progress, or state-dependent primary CTA |
| Toolbar truncation | Too many long lifecycle actions competed for horizontal space; freeze label and secondary actions remained visually heavy |
| Comment-panel collapse | Flat vertical checklist + capped `QPlainTextEdit` heights inside a non-splitter `QHBoxLayout` let the ionogram shrink to a strip and editors collapse under stretch pressure |

---

## Guided Review redesign

- Centered workflow card (`guided_card`) — never blank.
- Four-step labeled header: Composition → Blind review → Comparison → Summary/export (✓ / ● / ○).
- Stage title, explanation, progress text + labeled progress bar.
- State-dependent primary actions (RU/EN):
  - no cohort → Select/create / Go to Cohorts
  - draft empty → Add frames
  - draft with items → Freeze and start blind review
  - frozen pending → Continue blind review
  - comparisons pending → Go to comparison
  - complete → Open summary
- Primary action navigates/performs the required step (freeze → Rapid + first unfinished; continue → Rapid; comparison → compare tab; summary → Summary).

---

## Rapid Review responsive layout

- Horizontal `QSplitter` (table min ~520, right min ~440, children not collapsible).
- Compact 8-column table + horizontal scroll; optional columns not forced.
- Right panel: one intentional vertical scroll + sticky save footer.
- Ionogram `minimumHeight` 240; identity label; Open larger.
- Localized inactive-cell values via `display_label`.
- Splitter state restore/save via session settings when available.

---

## Grouped comment builder

Four collapsible groups (trace / morph obs / interference / limits) with selected counts.  
Preset + Apply + Clear + Expand/Collapse all (⋯).  
Editors with real minimum heights:

- Generated comment (read-only + refresh)
- Final expert comment (editable; dirty guard)
- Expert’s own description

Presets still do not select final morphology. Final edited text is not overwritten silently.

---

## Toolbar finalization

Visible: Preview + Freeze/Continue + `⋯` overflow.  
Create/Add/Remove/Clear/Delete/Revision/Archive/Export/Validate/Refresh in overflow.  
Filters (archived / legacy) under Filters submenu.  
Overflow has tooltip + accessible name.

---

## Supported size/scale matrix (automated contracts)

Automated checks cover splitter minima, editor minima, compact columns, sticky save, overflow visibility.  
**Owner must still confirm visually** at:

- 1280×720 @ 90%
- 1366×768 @ 100%
- 1600×900 @ 100%
- 1920×1080 @ 100%
- 1920×1080 @ 125%
- Owner’s current interface scale from user settings

---

## Tests

Focused: `tests/test_phase4c2b1_*` — **31 passed**.  
Phase 4C.2 family: **89 passed** (`-k phase4c2`).  
Full suite: **612 passed**.

Warning audit (`python -W default -m pytest tests -k phase4c2 -q`):  
**106** `ResourceWarning: unclosed database` (pre-existing SQLite connection pattern; not globally suppressed).

---

## Validators

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature shadow mode | OK |
| Morphology candidate shadow | OK |
| Morphology review corpus | OK |
| i18n | OK |
| docs | passed |
| hygiene | 0 violations |

---

## Packaged smoke (synthetic/project fixtures)

Automated size-contract checks ≠ owner visual confirmation.

Checklist for packaged EXE:

1. Open Guided with no selected cohort → card explains next step  
2. Select draft → freeze-and-start card visible  
3. Freeze and start → Rapid table + ionogram  
4. Resize across matrix  
5. Apply preset; expand/collapse groups  
6. Verify three comment text areas; edit final  
7. Save and next; candidate remains hidden  
8. Overflow at each size; no truncated action loss  
9. RU/EN switch  
10. Complete round one + comparison → Summary  
11. No Not Responding  

---

## Visual checks still requiring owner confirmation

- Guided card readability at 90–125% scale (dark/light)
- Ionogram never becomes a thin strip at owner window size
- Comment editors remain usable heights
- Toolbar buttons never clip into unreadable fragments
- Sticky save remains reachable without nested-scrollbar traps

---

## Git

- **No commit**
- **No push**

Scientific versions (candidate engine, geometry, feature registry) unchanged. Shadow-only preserved.
