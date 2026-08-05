# Phase 4C.2b — Acceptance Report

**Build Identity:** `4C.2b`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2a.1):** `D764CBCFD66ED8F0EEB1D004FB70C52449F3D0B85D08C35CB7F68B098E295690`  
**New EXE SHA-256:** `55788895CAA9D28CE65768BC238DC50DFC112FE483E0F1698413845EE29F23B0`  

Owner visual QA is **not** claimed PASS.

---

## Owner findings addressed

| Finding | Resolution |
|---------|------------|
| Child revision appeared to contain parent review results | Root cause: **stale UI form/compare state** + **reused `item_id`s**. Review JSONL was never copied. Fixed: mint new item IDs, hard UI reset, `cohort_id` lookup isolation, repair migration |
| Too many tab switches / unclear order | **Guided review** default with stage indicator and primary actions |
| Truncated toolbar buttons | Responsive bar: preview + freeze primary + `⋯` overflow |
| Comparison raw English/codes in RU | Localized comparison cards via `display_label` / `format_comparison_cards` |
| Summary raw JSON | Human-readable dashboard; Technical JSON only via overflow |
| Rapid table + structured comments missing | Rapid Review Table + comment builder/presets/types |
| Freeze/UI localization gaps | Additional RU/EN keys; custom dialog buttons |

---

## Revision leakage root cause

**Not** physical copy of `blind_reviews.jsonl` / comparisons. Domain already created empty review stores and reset `item_status`.

Owner-visible leak came from:
1. UI keeping morphology/compare widgets after revision create (`_cohort_id` set before clear → stale form).
2. Reused parent `item_id`s making leftover UI look cohort-valid.
3. Incomplete `_clear_stale_views` (did not reset form / `_blind_locked_for_item`).

### Repair / migration
`detect_revision_leakage` + `repair_revision_integrity`:
- quarantine non-empty child review JSONLs;
- remint colliding item IDs;
- force pending statuses;
- never mutate frozen parent.

---

## Guided workflow

Stages: composition → blind review → comparison → summary/export.  
Primary actions: freeze-and-start; save-and-next; go to comparison; save comparison and next; export/validate.  
Default tab: Guided.

---

## Strict cohort blinding

New protocol default: `strict_cohort_blinding`.  
Legacy `after_blind_lock` maps to `per_item_reveal`.  
Reveal policy frozen with protocol hash; draft-only change.  
`can_reveal_candidate` enforces full round-one before any reveal under strict policy.

---

## Rapid Review + comments

- Shared draft between table and detail panel
- Structured codes (trace / morphology obs / interference / limits)
- Generated + editable final text; expert own description separate
- Presets never auto-select morphology
- Append-only `comments.jsonl` with types, hashes, supersession
- Shortcuts documented in Help

---

## Comparison + Summary

Localized cards (expert / candidate / strength / agreement).  
Engine under Technical details.  
Summary cards + distributions; honest undefined second-review agreement.  
No accuracy/F1 in human UI.

---

## Tests

- `tests/test_phase4c2b_revision_integrity.py`
- `tests/test_phase4c2b_guided_blinding.py`
- `tests/test_phase4c2b_comments.py`
- `tests/test_phase4c2b_ui_summary.py`

| Suite | Result |
|-------|--------|
| Full `pytest tests` | **581 passed** |
| Warning audit (4C.2*) | **58 passed, 44 warnings** (pre-existing sqlite ResourceWarnings; not newly introduced domain bugs; not suppressed) |

---

## Validators / hygiene

| Check | Result |
|-------|--------|
| Registry | 93/93 |
| Geometry | 17/17 |
| Shadows | OK |
| Corpus | OK (fixture updated for strict blinding) |
| i18n | OK |
| docs | passed |
| hygiene | 0 violations |

Scientific versions unchanged.

---

## Packaged smoke

EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
SHA-256: `55788895CAA9D28CE65768BC238DC50DFC112FE483E0F1698413845EE29F23B0` (≠ prior)

Automated domain smoke: draft → freeze → strict blind gate → presets/comments → full round-one → localized comparison → human Summary → editable revision with empty child reviews → integrity OK.

Interactive owner checks still required for: visual ionogram, RU dialog polish, responsive overflow under real window sizes, no Not Responding.

---

## Git

- **No commit**
- **No push**

---

## Owner QA still required

Use updated `docs/PHASE4C2_OWNER_QA.md`. Do not treat this report as visual PASS.
