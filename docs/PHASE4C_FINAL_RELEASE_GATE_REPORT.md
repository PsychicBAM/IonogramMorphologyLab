# Phase 4C Final Release Gate Report

**Date:** 2026-08-05  
**Final Build Identity:** `4C.3a.2` (unchanged — test-expectation alignment only; no product source fix required)  
**Mode:** shadow-only  
**Owner visual QA:** **PASS** (confirmed for 4C.3a.2 workflow)  
**GitHub CI:** not claimed (no commit/push)

---

## Accepted phases

- 4C.2  
- 4C.2a  
- 4C.2a.1  
- 4C.2b  
- 4C.2b.1  
- 4C.2b.2  
- 4C.2b.3  
- 4C.3  
- 4C.3a  
- 4C.3a.1  
- 4C.3a.2  

---

## Full pytest result

| Metric | Value |
|--------|--------|
| Command | `python -m pytest` |
| Collected | 695 |
| Passed | **695** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** |
| xpass | **0** |
| Duration | 469.15s (~7m49s) |

### Gate procedure note

1. Initial full suite: **7 failed / 688 passed** — all failures were **stale test expectations** for prior Build Identity `4C.2b.3` and pre-batch Guided CTA labels (`Start comparison`), not product regressions.  
2. Fixed only those test assertions to current accepted contracts (`4C.3a.2`, `batch_reveal_compare` / Reveal Candidates…).  
3. Focused re-run of the 7 tests: **7 passed**.  
4. Full suite re-run once: **695 passed**.

### Warnings (honest)

Normal full pytest summary showed **no warnings section**.  
No repository-wide `-W default` audit was run (per gate instructions).  
Historical SQLite `ResourceWarning`s remain known from some UI fixtures using `create_project`; they were **not** globally suppressed.

---

## Validators

| Validator | Result |
|-----------|--------|
| Feature registry v2 | **93/93** |
| Synthetic geometry v2 | **17/17** (`iml2-0.2.0`) |
| Feature shadow mode | **OK** |
| Morphology candidate shadow | **OK** |
| Morphology review corpus | **OK** |
| Morphology review campaign | **OK** |
| i18n | **OK** |
| docs | **PASS** |
| repository hygiene | **0 violations** |

---

## Scientific contract audit

| Contract | Status |
|----------|--------|
| shadow-only mode | OK (`shadow_only=True`) |
| scientifically_validated = false | OK |
| production RuleEngine unwired | OK (no production RuleEngine wiring hits) |
| Geometry version `iml2-0.2.0` | OK (`FEATURE_VERSION`) |
| Candidate engine `iml-morph-candidate-0.1.1` | OK |
| Ruleset `iml-morph-candidate-rules` / `0.1.0` | OK |
| No threshold tuning / training | OK |
| No accuracy/F1/sensitivity/specificity claims | OK (descriptive-only summary notes) |
| Candidate ≠ ground truth | OK |
| Source MAT read-only | OK |
| Blind review immutable / append-only | OK |
| Reveal blocked before required blind round | OK (`can_reveal` / batch gate) |
| Batch comparison idempotent | OK |
| Current-state counts ≤ eligible items | OK (`project_cohort_comparisons.current_count`) |
| Corrected reviews/comparisons do not inflate completion | OK |
| Second reviewer optional/separate | OK |
| Campaign Resume uses current state / batch CTA | OK |
| Campaign source picker = project inventory (no manual SHA) | OK |
| No candidate leakage into blind views | OK |

---

## Regression hotspot static audit

| Hotspot | Result |
|---------|--------|
| No raw `len(comparison_history)` as current progress | OK — progress uses `current_count`; history length only for consistency/diagnostics |
| Unique current `(cohort_id, item_id)` state | OK |
| No first-MAT fallback for active source | OK — `selected_mats[0]` only in inventory remove-entry helper when snap path missing, not activation |
| No stale project-local source authority on Campaign page | OK — live session + signals |
| No reused child revision item IDs | OK (prior phase contracts retained) |
| Lookups include cohort identity | OK |
| No duplicate signal connections causing duplicate saves | OK (guarded comparison save) |
| No blank CTA from missing keys | OK (batch keys present EN/RU) |
| No raw canonical codes in normal RU UI | OK (localized states / validation issues) |
| No editable source SHA in normal Campaign wizard | OK (`has_editable_sha_field` → False path) |
| No large always-open Technical Details | OK (toggle / overflow) |
| No owner paths in scientific exports | OK (export tests + validator hygiene) |
| No user campaign/corpus/runtime data tracked | OK — excluded from intended commit set |

---

## Build / package

| Item | Value |
|------|--------|
| Source Build Identity | `4C.3a.2` |
| Frozen Build Identity | `4C.3a.2` |
| EXE path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` |
| Final EXE SHA-256 | `1B4C861A43B1E0A14AE4CF5436393F87B70091F284EEB9E981531E5749F6DC60` |
| Owner-verified prior SHA | `5A3BBC920AB2684CC6B79CB4D02F2132D9DF0B9AD5A66D7255EC988A5A8A081A` |
| SHA note | Clean rebuild SHA **differs** from owner-verified SHA (expected) |
| Packaged start | EXE launched and remained running (then stopped) |
| Owner MAT embedded | None found under `dist\` |
| Campaign/corpus modules in Analysis TOC | Present (`batch_compare`, `project_sources`, campaign/corpus UI) |

---

## Packaged / domain smoke

**Automated smoke (synthetic fixtures only)** — distinct from owner visual QA:

1. Domain: 5-item cohort → blind lock → batch reveal/compare → **5/5**  
2. Repeat batch → remains **5/5**  
3. Optional post-comparison note → current count still **5**  
4. `validate_cohort` issues: **0**  
5. Packaged EXE process start: **OK**  
6. Full interactive RU wizard / Campaign UI path inside packaged EXE: **not re-run here**; covered by **owner visual QA PASS**

---

## Git review

| Check | Result |
|-------|--------|
| `git status --short` | Reviewed (~176 status lines) |
| `git diff --stat` | Reviewed |
| `git diff --check` | No whitespace errors reported for intended paths |
| Staged | **0** |
| Commit | **not performed** |
| Push | **not performed** |

### Intended inclusion (**95 files** with `--untracked-files=all`)

Exact count for a future commit of Phase 4C.2–4C.3a.2 (status paths expanded):

- `src/ionogram_morphology_lab/morphology_review_corpus/**`  
- `src/ionogram_morphology_lab/morphology_review_campaign/**`  
- `src/ionogram_morphology_lab/ui/expert_review_*.py`, `active_source_authority.py`, `corpus_display.py`, `review_ionogram_view.py`, `build_identity.py`, related `session.py` / `main_window.py` / `feature_diagnostics_page.py` / `help/content.py`  
- `src/ionogram_morphology_lab/i18n/en.json`, `ru.json`  
- `scripts/validate_morphology_review_corpus.py`, `validate_morphology_review_campaign.py`  
- `docs/PHASE4C*` acceptance/QA reports (including this gate report)  
- `tests/test_phase4c2*`, `tests/test_phase4c3*`  
- Gate-aligned identity/CTA expectation updates in three `tests/test_phase4c1e*.py`  
- `.gitignore` (if campaign/corpus ignore rules are part of the phase)

### Explicit exclusions

- `config/user_settings.json`  
- owner MAT files  
- owner `review_dataset` runtime data  
- owner morphology campaigns / corpora  
- generated campaign exports  
- local databases / caches  
- egg-info  
- `matlab_builtin` churn  
- `matlab_studio_library` user/imported/version data  
- `user_library`  
- synthetic MAT binary regeneration (unless intentionally required)  
- temporary files / performance dumps / verification ZIPs  
- `_git_*_gate.txt` scratch files from this gate  

---

## Release readiness

**READY for commit/push from a verification standpoint**, subject to the owner explicitly requesting commit/push.

Remaining non-blockers:

- GitHub CI not yet exercised (requires push).  
- Packaged interactive UI smoke partially deferred to already-completed owner visual QA.  

**No commit. No push.**
