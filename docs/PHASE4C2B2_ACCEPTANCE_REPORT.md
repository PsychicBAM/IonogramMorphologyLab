# Phase 4C.2b.2 — Acceptance Report

**Build Identity:** `4C.2b.2`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2b.1):** `D97A54914F1B71E4C1AEFE900F624C64433A0AB2E3C0AB3DB90112223E7BC609`  
**New EXE SHA-256:** `DDF881E809D9D51D4A506FB758B47BEEF6BACB5ECDF6DC2BF5A8FF99D983E346`  

Owner visual QA is **not** claimed PASS. This phase is a narrow owner-workflow closure.

---

## Owner findings (after 4C.2b.1)

Accepted from 4C.2b.1: Guided card, Rapid table/splitter, comment groups/editors, toolbar overflow, RU/EN, no Not Responding, candidate hidden during blind review.

Remaining defects addressed here:

1. Guided Comparison CTA visually blank after 5/5 blind reviews.
2. Guided card did not clearly show blind 5/5 and comparisons 0/5 with an exact next action.
3. Unclear post-blind handoff.
4. Legacy Review tab showed empty-looking fields and “Save blind review” on locked items.
5. Save on locked review leaked raw domain exception about `revision_reason`.
6. No explicit corrected-review workflow.
7. RU gaps: `per_item_reveal`, Save draft / Draft saved, raw revision messages, technical IDs in normal UI.

---

## Root causes

| Symptom | Root cause |
|---------|------------|
| Blank comparison CTA | `_sync_guided_and_refresh` mapped labels for `go_to_comparison` but not `save_comparison_next`; `labels.get(action, "")` set empty button text while remaining enabled |
| Locked Review empty/save | Review tab had no read-only detail surface; shared Rapid form looked empty/editable; Save called `save_blind_review` without revision fields → domain exception |
| Raw policy code | Guided cohort line printed normalized policy string (`per_item_reveal`) instead of localized labels |

---

## Guided comparison handoff

- Stage title: Candidate comparison / «Сравнение с кандидатом»
- Dual progress: blind completed + comparisons completed
- CTA never blank:
  - 0 comparisons → Start comparison / «Начать сравнение»
  - partial → Continue comparison / «Продолжить сравнение»
  - complete → Open summary / «Открыть сводку»
- Click opens Comparison tab, loads first uncompared item, keeps candidate hidden until explicit Reveal
- Save comparison advances to next uncompared item without auto-reveal
- Policy shown as readable RU/EN labels (frozen protocol unchanged)

---

## Locked Review detail

- Tab purpose: Review details / «Подробности оценки»
- Locked badge, banner, localized saved fields, comments, provenance
- Technical IDs under expandable Technical details
- Generic Save blind review hidden when locked
- Pending / no-item states localized and non-blank

---

## Explicit corrected review revision

- Action: Create corrected review revision / «Создать исправленную версию оценки»
- Requires non-empty reason; cancel creates no record
- Original locked review unchanged; new record has `prior_review_id` + `revision_reason`
- Post-reveal corrections set `post_reveal_revision`
- Locked Save path offers create-revision dialog; raw English domain text not shown

---

## Localization

- Save draft → «Сохранить черновик»
- Draft saved → «Черновик сохранён»
- Policy labels: strict / per-item readable in RU and EN
- Comparison/correction/progress strings covered by i18n parity

---

## Tests

Focused `phase4c2b2`: **19 passed**  
Phase 4C.2 family: **108 passed**  
Full suite: **631 passed**

Warning audit (`-W default -k phase4c2`): **144** SQLite `ResourceWarning`s (pre-existing pattern; not globally suppressed).

---

## Validators

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature shadow | OK |
| Morphology candidate shadow | OK |
| Morphology review corpus | OK |
| i18n | OK |
| docs | passed |
| hygiene | 0 violations |

---

## Packaged smoke (synthetic fixtures)

Automated ≠ owner visual confirmation.

1. Freeze 5-item cohort; complete 5 Rapid blinds  
2. Guided shows blind 5/5, comparisons 0/5, Start comparison  
3. Click → first uncompared item; candidate hidden until Reveal  
4. Save comparison and next through all five  
5. Guided → Summary stage  
6. Inspect locked item in Review details (read-only; Save hidden)  
7. Create corrected revision with reason; original unchanged  
8. No raw English revision exception; RU/EN OK; no Not Responding  

---

## Owner visual checks still required

- Comparison CTA visible/readable at owner scale
- Reveal → compare cards → save-and-next flow
- Locked Review details clarity
- Correction dialog UX in RU
- No truncated/blank Guided CTA after language switch

---

## Git

- **No commit**
- **No push**

Scientific versions unchanged. Shadow-only preserved.
