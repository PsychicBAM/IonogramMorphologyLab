# Phase 4C.2b.3 — Acceptance Report

**Build Identity:** `4C.2b.3`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2b.2):** `DDF881E809D9D51D4A506FB758B47BEEF6BACB5ECDF6DC2BF5A8FF99D983E346`  
**New EXE SHA-256:** `8758777CBCEFFCC3BE41DBCF38D8A21D5CB24829968B82983274A34BB8B5DFCB`

Owner visual QA is **not** claimed PASS. This phase corrects a real owner-data progress/integrity defect and closes comparison/UX semantics.

---

## Owner findings (after 4C.2b.2)

Accepted from 4C.2b.2: Guided blind review, Rapid Review, strict candidate hiding, comments/presets, embedded ionogram, Comparison handoff, explicit reveal, localized cards, locked Review details, corrected review revision, RU/EN, no Not Responding.

New defects addressed here:

1. Five-item corpus showed comparisons `6/5` → `9/5` → `10/5`.
2. Summary reported six completed comparisons and six candidate-label records for five items.
3. Queue had five rows — counters were not based on distinct current items.
4. Repeated “Save comparison and go to next” created/counted duplicate history.
5. Before reveal, Comparison showed “Expert abstained”.
6. After reveal, generic “Comparison impossible” without reason.
7. Unclear whether a second reviewer is required (it is not for human-vs-candidate).
8. Optional second-review experiment must stay separate from comparison progress.
9. Queue statuses (`Locked` / `Waiting` / `Yes`) were ambiguous across workflow stages.
10. Review Details Technical panel consumed unnecessary horizontal space.
11. Guided used a narrow card with large empty canvas.

---

## Exact duplicate-count root cause

Reproduced on a five-item cohort: five blinds → save comparison for item 1 twice → inspect JSONL / Guided / Summary.

| Layer | Defect |
|-------|--------|
| `store.reveal_and_compare` | Always appended a new `RevealComparison` (new UUID); no idempotency / supersession |
| `workflow.determine_workflow_stage` | Used `n_cmp = len(reveal_comparisons.jsonl)` (raw history rows) |
| `analytics.descriptive_summary` | Counted all raw comparison rows for progress and distributions |
| Model | No comparison revision / supersession fields |

Not caused by: duplicate item IDs, reveal-as-comparison, second-review mixing into comparison JSONL, or silent UI-only increments. UI double-clicks amplified the domain append bug; language/tab switches did not independently invent rows once domain idempotency exists.

**Raw history vs current state:** append-only `reveal_comparisons.jsonl` may contain many rows; dashboards must use one current non-superseded record per `(cohort_id, item_id)`.

---

## Current-state projection

Authoritative module: `morphology_review_corpus/current_state.py`.

- `project_comparisons` / `project_cohort_comparisons` → one current row per item
- Explicit supersession via `supersedes_comparison_id` / `prior_comparison_id`
- Legacy duplicates (no chain): last file-order row current; identical vs conflicting reported
- Invariant: `0 ≤ completed_count ≤ eligible_item_count ≤ cohort_item_count`
- On failure: integrity warning + duplicate/conflict diagnostics — **no silent clamp** of `10/5` to `5/5`

Workflow, Guided, Queue, Summary, and Review Details refresh from this projection (no manual counter increments; no MAT rescans).

---

## Idempotent comparison save

`reveal_and_compare` identity check (same current logical payload → return existing; no append):

- `cohort_id`, `item_id`, locked `review_id`
- human morphology / candidate state / agreement status
- notes + comment; `candidate_result_hash` stored on record
- `comparison_contract_version` on model

After success: Save disabled; read-only «Сравнение сохранено»; next uncompared item selected. UI `_comparison_save_guard` blocks re-entrancy; domain layer enforces idempotency even if UI is invoked again.

---

## Explicit comparison correction

Advanced action: «Создать исправленную версию сравнения» / “Create corrected comparison revision”.

- Non-empty reason required
- Original row unchanged; new row references prior comparison ID
- Only newest non-superseded counts as current → progress stays one per item
- History export retains all versions

---

## Repair for existing corpora

Action: «⋯ → Проверить и восстановить производное состояние» / “Validate and repair derived state”.

- Non-destructive inspection by default; repair writes `comparison_current_state.json` + audit
- Does **not** delete JSONL history; frozen manifest unchanged
- Identical duplicates → one canonical current; others marked non-current in projection metadata
- Conflicting duplicates → reported; documented `latest_valid` policy with repair event
- Second repair is idempotent

Owner path: open affected five-item corpus → overflow repair → confirm Guided/Summary ≤ `5/5`.

---

## Abstention / agreement semantics

| Timing | Status |
|--------|--------|
| Before reveal | `comparison_pending_reveal` — «Кандидат ещё не показан. Сравнение не выполнено.» |
| Definite vs definite | `exact_agreement` / `morphology_disagreement` |
| Human indeterminate | `human_abstained` + explanation |
| Human not assessable | `not_comparable` with reason |
| Candidate abstained | `candidate_abstained` |
| Both abstained | `both_abstained` |
| Candidate missing | `candidate_unavailable` |

No generic unexplained “Comparison impossible”.

---

## Optional second reviewer

Primary workflow needs: one locked round-one review + candidate snapshot + saved comparison.

Guided/Summary state clearly that a second independent expert is **not** required for candidate comparison (only for inter-reviewer agreement / adjudication). Action moved under overflow: «Дополнительное исследование → Назначить второго эксперта». Same reviewer blocked as independent second; second-review counts do not affect first-round or comparison progress.

---

## Queue / Guided / Technical Details

- Queue columns: First blind review, Candidate reveal, Comparison, Second independent review, Adjudication — localized values, no generic “Yes” for comparison
- Guided card: responsive ~680–900 px with Completed / Current step / Optional research / Scientific reminder
- Review Details Technical section: collapsed by default («Технические сведения»); no large reserved panel while closed

---

## Tests

| Suite | Result |
|-------|--------|
| `tests -k phase4c2b3` | **19 passed** |
| `tests -k phase4c2` | **127 passed** |
| Full `pytest` | **650 passed** |
| Warning audit (`-W default -k phase4c2`) | **156** SQLite `ResourceWarning`s (pre-existing pattern; not globally suppressed) |

Covered: idempotency, double-click/re-entry, correction, five-item current counts, repair fixture (10 raw → ≤5 current), semantics, second-review isolation, queue/tech/Guided UI.

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

Automated domain smoke (≠ owner visual confirmation):

1. Five-item cohort; five blinds; five comparisons  
2. Double-save each comparison → still `5/5`  
3. Summary comparisons / candidate distribution / agreement totals = 5  
4. Corrected comparison with reason → still `5/5`  
5. Optional second review → comparison remains `5/5`  
6. Pre-reveal pending text; post-reveal `human_abstained` for indeterminate  
7. Injected identical + conflicting legacy duplicates → repair → current ≤ 5  
8. Build Identity `4C.2b.3`; EXE SHA differs from 4C.2b.2  

Owner still needs visual confirmation of Guided width, Technical collapse, Queue labels, RU/EN, and no Not Responding.

---

## Owner visual checks still required

- Progress never exceeds `N/N` on real five-item corpus after repair  
- Pre-reveal never shows abstention  
- Post-reveal statuses carry reasons  
- Optional second-reviewer wording  
- Queue column clarity  
- Wider Guided panel; collapsed Technical details  
- RU/EN after language switch without resave  

---

## Git

- **No commit**
- **No push**
- Nothing staged for this phase
- Unrelated MATLAB / `config/user_settings.json` / owner MAT churn remain unstaged and must not be committed with this phase

Scientific versions unchanged. Shadow-only preserved. No accuracy/F1 claims.
