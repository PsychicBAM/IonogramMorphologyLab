# Phase 4C.3 — Acceptance Report

**Build Identity:** `4C.3`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2b.3):** `8758777CBCEFFCC3BE41DBCF38D8A21D5CB24829968B82983274A34BB8B5DFCB`  
**New EXE SHA-256:** `CA08E26476EEAE37AD20753727E5E682F1CA72A57F50A8A5B6AC6D76778CCCC2`

**Verification mode:** time-constrained targeted verification.  
**Full pytest suite deferred due to time-constrained development window.**  
Full-suite regression is mandatory before the later combined 4C.2–4C.3 commit/push.  
Do **not** claim complete regression verification.

Owner visual QA is **not** claimed PASS.

---

## Objective

Make the operational morphology review corpus practical for a real pilot expert-review campaign across many dates, sources, and frames — without scientific validation claims, threshold tuning, training, or production RuleEngine enablement.

---

## Regression-prevention checklist (used during implementation)

| Area | Guard |
|------|--------|
| A. Active-source authority | Wizard uses `authoritative_active_source()`; no first-MAT fallback |
| B. Current-state counting | Campaign progress uses `project_cohort_comparisons` / locked reviews per `(cohort_id, item_id)` — never raw JSONL lengths |
| C. Cohort revision isolation | Campaign links cohorts by ID + manifest hash; deletion does not delete frozen cohorts |
| D. UI state | Resume navigates into existing Guided/Rapid/Comparison; refresh from domain state |
| E. Blinding | Campaign queue omits candidate class/colour; preview sets `candidate_fields_present=False` |
| F. Localization | Campaign nav/UI keys in RU/EN; designation bilingual |
| G. Layout | Dashboard panel 680–960 px; Resume CTA always labeled |
| H. Portability / hygiene | Campaigns under project `review_dataset/morphology_campaigns/` (gitignored); no absolute paths in exports |

---

## Campaign schema

Storage:

```
{project}/review_dataset/morphology_campaigns/<campaign_id>/
  campaign.json
  campaign_protocol.json
  cohort_links.jsonl
  assignments.jsonl
  campaign_audit.jsonl
  exports/
```

Package: `morphology_review_campaign/`  
States: draft / ready / active / paused / completed / archived (independent of cohort freeze).

Default designation:

- EN: “Pilot expert-review campaign — not a scientific validation study.”
- RU: «Пилотная кампания экспертной оценки — не является научной валидацией.»

---

## Campaign / cohort relationship

- Campaign creates or links morphology cohorts (roles: first_review, second_review, holdout_descriptive, adjudication_subset).
- Links store exact `cohort_id` + `manifest_hash`.
- Campaign deletion does not delete frozen cohorts.
- Existing corpus store/freeze/current-state APIs are reused — no second corpus system.

---

## Creation wizard

Nav: **Expert Review Campaigns** / «Кампании экспертной оценки»  
Action: **New Expert Review Campaign** / «Новая кампания экспертной оценки»

Steps: Basic → Sources → Time windows → Sampling → Experts → Preview → Create  
Preview is candidate-independent. Creation requires Finish confirmation.

---

## Sampling

Methods: manual, all_eligible, deterministic_random, stratified, imported_manifest.  
Records seed, counts, stratum, inclusion reason, related-frame groups.  
Warns when adjacent frames of one sequence appear as independent samples.  
Option: keep adjacent frames together across experts.  
Target count is operational only — not a scientifically required N.

---

## Dashboard / Resume / Queue

- Progress cards: planned, unique eligible, blind, comparison, optional second, adjudication, unavailable, integrity.
- **Resume Work** routes: composition → first blind → comparison → optional second (if assigned) → summary/export.
- Never auto-reveals candidate; never jumps to completed items by default.
- Campaign queue uses explicit localized statuses (no generic “Yes”); blind-safe (no candidate class).

---

## Optional second reviewer

Clearly stated in dashboard and protocol: not required for human-versus-candidate comparison; only for inter-reviewer agreement / adjudication.

---

## Descriptive summary & readiness export

- Campaign descriptive summary aggregates current-state cohort summaries.
- Export: `campaign_readiness_report.md` + `.json` (portable, no absolute paths, no MAT payloads).
- Accuracy/F1/etc. unavailable with explicit explanation helper.

---

## Integrity validator

`scripts/validate_morphology_review_campaign.py` — synthetic fixtures only.  
Also `validate_campaign()` domain API: schema/hashes, links, count invariants, no RuleEngine wiring, no prohibited metric keys.

---

## Focused tests

| Suite | Result |
|-------|--------|
| `test_phase4c3_campaign_*.py` | **16 passed** |
| High-risk regressions (4C.3 + selected 4C.2b/4C.2a) | **48 passed** |
| Focused warning audit (`-W default` on 4C.3 tests) | **no Phase-4C.3-introduced ResourceWarnings** (only pre-existing pytest-asyncio config deprecation from environment) |

**Full pytest suite:** deferred (not run in this phase).

---

## Validators

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature shadow | OK |
| Morphology candidate shadow | OK |
| Morphology review corpus | OK |
| Morphology review campaign | OK |
| i18n | OK |
| docs | passed |
| hygiene | 0 violations |

---

## Static regression audit

| Check | Result |
|-------|--------|
| No raw-history `len(comparisons)` in campaign progress | OK |
| Current counts group by cohort_id/item_id | OK |
| No first-source fallback in campaign wizard | OK |
| No candidate fields in blind campaign queue/preview | OK |
| Cohort lookups include cohort_id | OK |
| Frozen cohort not deleted with campaign | OK |
| No absolute paths in readiness export | OK |
| Campaigns gitignored | OK |
| No scientific performance claim keys | OK |
| No production RuleEngine import of campaign package | OK |

---

## Build

- Build Identity: `4C.3`
- Geometry: `iml2-0.2.0` (unchanged)
- Candidate engine: `iml-morph-candidate-0.1.1` (unchanged)
- Ruleset: `iml-morph-candidate-rules 0.1.0` (unchanged)
- `shadow_only = true`, `scientifically_validated = false`
- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`
- SHA-256: `CA08E26476EEAE37AD20753727E5E682F1CA72A57F50A8A5B6AC6D76778CCCC2` (≠ 4C.2b.3)

---

## Packaged smoke (synthetic)

Automated domain smoke (≠ owner visual):

1. Create campaign with two synthetic sources + time window  
2. Deterministic sample (seed 42) → preview unique items  
3. Create/link first-review cohort; open progress dashboard data  
4. Resume → first blind; complete one review; progress uses unique current counts  
5. Second reviewer marked optional  
6. Export readiness; campaign validator OK  

---

## Explicit deferred gate

**Targeted verification passed; full-suite regression is deferred due to the owner’s time-constrained development window.**

Full `python -m pytest` (and repository-wide warning audit) **must** be run before commit/push of the combined 4C.2–4C.3 work.

---

## Git

- **No commit**
- **No push**
- Staged count: 0  
- Do not stage owner MAT/corpora/campaign runtime data, `config/user_settings.json`, MATLAB churn, regenerated synthetic binaries, local DBs, or exports.
