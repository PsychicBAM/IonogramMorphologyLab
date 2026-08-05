# Phase 4C.3a.2 — Acceptance Report

**Build Identity:** `4C.3a.2`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.3a.1):** `A5CA0222A03406F15FBF75BBF77422AD5D988763540ADC5FCAD0F39D1ED9C061`  
**New EXE SHA-256:** `5A3BBC920AB2684CC6B79CB4D02F2132D9DF0B9AD5A66D7255EC988A5A8A081A`

**Verification mode:** time-constrained targeted verification.  
**Full pytest suite deferred** until after this phase and before commit/push.  
Owner visual QA is **not** claimed PASS.

---

## Owner explanation

Phase 4C.3a.1 owner visual QA passed (wizard, inventory, hydration, counters).  
The remaining issue: after all blind reviews, the owner had to open Comparison, click Reveal, and click Save for **every** item. That is unnecessary — comparison status is deterministic.

---

## Why comparison is deterministic

Status is derived only from:

1. the immutable locked first blind review;  
2. the immutable frozen candidate snapshot;  
3. the existing `comparison_status(...)` contract.

No additional human scientific decision is required for exact agreement, morphology disagreement, abstentions, not comparable, or candidate unavailable.

---

## Batch reveal workflow

Primary action after blind-round completion:

- RU: «Показать кандидатов и рассчитать сравнения»  
- EN: “Reveal Candidates and Calculate Comparisons”

Localized confirmation, then `batch_reveal_and_compare` calls existing `reveal_and_compare` per eligible item. Opens Summary on completion. Refreshes Guided / Queue / Campaign views.

Campaign Resume Work routes to this batch action (`action=batch_reveal_compare`, Guided tab).

---

## Optional-note separation

Deterministic comparison is saved without a required “Save comparison”.  
Optional «Комментарий после сравнения» / “Post-comparison note” is saved separately via `save_post_comparison_note` (append-only revision). It does **not** change comparison class or current comparison count.

Per-item mode remains under **⋯ → Покадровое сравнение** / **More → Per-item Comparison**. Reveal there derives comparison immediately; next item is not auto-revealed.

---

## Idempotency

Repeated batch invocation reuses current comparisons (`reused_count`).  
Current comparison count never exceeds eligible items.  
Optional notes append history but keep `current_count` stable.

---

## Unavailable candidates

Eligible items are compared; unavailable candidate snapshots yield `candidate_unavailable` and are listed separately (`Сравнено X из Y; для N кадров кандидат недоступен`).

---

## Focused tests

| Suite | Result |
|-------|--------|
| `test_phase4c3a2_batch_compare.py` | **10 passed** |
| Warning audit on 4C.3a.2 | Clean (only env pytest-asyncio deprecation) |
| Guided / resume / idempotency / semantics / blinding / dashboard | **37 passed** (with set) |

**Full pytest:** deferred (mandatory once before commit/push).

---

## Validators

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature / candidate shadows | OK |
| Corpus / campaign validators | OK |
| i18n | OK |
| docs | passed |
| hygiene | 0 violations |

---

## Build

- Build Identity: `4C.3a.2`  
- Scientific versions unchanged; shadow-only  
- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
- SHA-256: see header (must ≠ 4C.3a.1)

---

## Packaged / domain smoke

Five-item synthetic cohort: blind complete → batch → 5/5 current comparisons → repeat stays 5/5 → optional note → count unchanged.

Owner visual QA of packaged RU/EN batch confirmation still required.

---

## Explicit deferral

**Targeted verification passed; full-suite regression is deferred due to the owner’s time-constrained development window.**

Full `python -m pytest` remains mandatory before commit/push.

---

## Git

- **No commit**  
- **No push**  
- Staged: 0  
