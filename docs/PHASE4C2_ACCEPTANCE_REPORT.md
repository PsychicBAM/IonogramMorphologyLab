# Phase 4C.2 — Acceptance Report

**Build Identity:** `4C.2`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Git:** no commit, no push (owner QA first)

## Phase objective

Build expert-review and corpus infrastructure to evaluate the morphology candidate engine against independently recorded human morphology assessments — without training, tuning, production RuleEngine wiring, or scientific validation claims.

## Architecture audit

Inspected and deliberately separated three stores:

| Store | Path | Role in 4C.2 |
|-------|------|----------------|
| Morphology candidate reviews | `{project}/feature_diagnostics/morphology_reviews/` | Existing FD morph reviews — not replaced |
| Geometry reviews | `{project}/feature_diagnostics/geometry_reviews/` | Pattern for supersession; **not** morphology GT |
| App-root owner `review_dataset` | app-level multi-axis labels | Different product; not auto-imported as GT |

**New corpus location (project-scoped, portable):**  
`{project}/review_dataset/morphology_corpora/<cohort_id>/`

## Reused existing components

- Candidate engine/ruleset identity constants (`iml-morph-candidate-0.1.1`, rules `0.1.0`)
- Geometry-style append-only / supersession thinking (implemented as JSONL prior_review_id chains)
- Project portability model (relative paths, SHA-256 source identity)
- Nav key `expert` → Expert Review Corpus page
- Help/`i18n` RU/EN systems
- Build Identity / packaging pipeline

## New corpus structure

```
review_dataset/morphology_corpora/<cohort_id>/
  cohort_manifest.json
  protocol.json
  items.jsonl
  candidate_snapshots.jsonl
  blind_reviews.jsonl
  reveal_comparisons.jsonl
  adjudications.jsonl
  audit_log.jsonl
  reviewers.json
  snapshots/
  exports/
```

## Schemas and versions

| Field | Value |
|-------|-------|
| Review corpus schema | 1 |
| Review record schema | 1 |
| Adjudication schema | 1 |
| Protocol schema | 1 |
| Corpus integrity contract | 1 |
| Geometry | iml2-0.2.0 (unchanged) |
| Candidate engine | iml-morph-candidate-0.1.1 (unchanged) |
| Candidate cache schema | 2 |
| Evidence ledger schema | 2 |
| Ruleset | iml-morph-candidate-rules 0.1.0 |
| Diagnostics layout schema | 2 |
| Sequence-state contract | 1 |

## Cohort protocol

Frozen protocol before review: purpose, pilot designation (EN/RU), inclusion/exclusion, sampling, blinding rules, allowed labels, reveal / second-review / adjudication policies, descriptive outputs allowed, **prohibited metrics**, candidate freeze, lock state.

Default designation:  
EN: *Pilot expert-review corpus — not a scientific validation set.*  
RU: *Пилотный корпус экспертной разметки — не является научно валидированным контрольным набором.*

## Sampling modes

- Manual selection  
- Random reproducible (sorted pool + seed + count)  
- Stratified pilot (e.g. by candidate_state for sampling only — not shown in blind UI)  
- Import CSV/JSON manifest (unavailable items retained with reason)

## Manifest freeze

Draft editable → **Freeze cohort** / «Зафиксировать корпус» → immutable. Revisions require new cohort ID + parent reference + reason.

## Review identity

Canonical identity: source SHA-256 + frame index, plus inventory IDs, feature/candidate hashes, stratum, partition (`pilot_review` / `future_holdout` / `excluded`), grouping fields for later leakage control.

## Blind workflow

Candidate class/strength/ledger/thresholds/agreement hidden until locked blind save. Procedural UI blinding (documented — not cryptographic). Ionogram and non-candidate layers remain available.

## Separate scientific axes

Morphology · Assessability · Interference · Ambiguity · Reviewer confidence (self-report) · optional observations. Primary decision is explicit, never auto-derived.

## Append-only history

JSONL reviews with `prior_review_id` supersession. Post-reveal revisions require `post_reveal_revision` + reason.

## Reviewer identities

Configurable `reviewer_id`, alias, role; no personal-name requirement. Same reviewer blocked as independent second reviewer by default.

## Second review / adjudication

Second reviewer cannot see first decision or candidate until both locked. Adjudication → **adjudicated expert reference** (never automatic ground truth). Candidate hidden until adjudication lock by default policy.

## Candidate snapshot freeze

Snapshots frozen at cohort freeze; no overwrite under another ruleset/engine.

## Reveal / comparison

After blind lock: Reveal → comparison statuses (`exact_agreement`, `morphology_disagreement`, …). Does not alter blind decision.

## UI entry points

Main nav **Expert Review Corpus** / **Корпус экспертной оценки** (`nav.expert`). Tabs: Cohorts, Queue, Review, Comparison, Summary.

## Descriptive analytics

Distributions, exact agreement counts, disagreement matrix, abstention rates, completion progress. Inter-reviewer descriptive match rate only with ≥2 independent dual-reviewed items and class variation.

## Prohibited scientific claims

No accuracy / precision / recall / sensitivity / specificity / F1 / validated performance. Refuse unsupported metric exports with explanation.

## Exports

Deterministic JSON/JSONL/CSV/Markdown/bundle under `exports/`. UTF-8, canonical codes, hashes, Build Identity, scientific non-claims. Blind export strips candidate fields. No absolute owner paths. No raw MAT.

## Audit log

Append-only events for create/freeze/review/reveal/compare/adjudicate/export/etc.

## Integrity validator

`scripts/validate_morphology_review_corpus.py` — schemas, hashes, reveal-after-lock, no RuleEngine wiring, blind-export leakage, synthetic fixture path.

## Files changed (principal)

**New package:** `src/ionogram_morphology_lab/morphology_review_corpus/`  
(`constants`, `labels`, `hashing`, `status`, `protocol`, `models`, `sampling`, `store`, `blinding`, `analytics`, `exports`, `integrity`)

**UI:** `ui/expert_review_corpus_page.py`, `main_window.py` (expert page), `build_identity.py`  
**i18n / help:** `i18n/en.json`, `i18n/ru.json`, `help/content.py`  
**Scripts:** `scripts/validate_morphology_review_corpus.py`  
**Tests:** `tests/test_phase4c2_review_corpus.py`, `tests/test_phase4c2_ui_smoke.py`  
**Docs:** this report, `docs/PHASE4C2_OWNER_QA.md`  
**Hygiene:** `.gitignore` for runtime `morphology_corpora`  
**Warning fix:** `review_dataset/schema.py` (`utcnow` → timezone-aware)

## Focused test results

```
python -m pytest tests/test_phase4c2_review_corpus.py tests/test_phase4c2_ui_smoke.py -q
19 passed
```

## Full pytest results

```
python -m pytest tests -q
542 passed in ~281–307s
```

Skipped: 0 (as reported by default `-q` run)  
Warnings (default pytest filter): none summarized as failures  
Warnings (`-W default` audit): ~388, almost all pre-existing `ResourceWarning: unclosed database` from Qt/matplotlib test teardown; one fixed `DeprecationWarning` (`datetime.utcnow` in owner `review_dataset/schema.py`). No global warning suppression. No scientific meaning changed to silence warnings.

## Validator results

| Validator | Result |
|-----------|--------|
| `validate_feature_registry_v2.py` | Registry 93/93 |
| `validate_synthetic_geometry_v2.py` | Synthetic Geometry 17/17 |
| `validate_feature_shadow_mode.py` | OK |
| `validate_morphology_candidate_shadow.py` | OK |
| `validate_morphology_review_corpus.py` | OK |
| `validate_i18n.py` | OK |
| `validate_docs.py` | passed |
| `check_repository_hygiene.py` | 0 violations |

## Build Identity

- release_phase: **4C.2**
- shadow_only: true
- scientifically_validated: false
- geometry / candidate / ruleset / layout / sequence contracts unchanged as listed above
- review corpus / record / adjudication / protocol / integrity schema versions: **1**

## Packaging

- Command: `powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1`
- Result: success  
- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
- New SHA-256:  
  **`8DAF2F0BC9FD2D8EAFA8D9047F709003439AF8AB68B1B3F6457710C2ACAB6815`**  
- Prior accepted SHA: `C2CBE0182251C302B2A07E130E4423F316B7500AB508CA867C84EE8B04631652` (differs ✓)  
- Package contains no `morphology_corpora` owner data; synthetic MAT under packaged `synthetic_data` only

## Packaged / synthetic smoke

| Check | Result |
|-------|--------|
| EXE exists | OK |
| `--smoke-test` | `Ionogram Morphology Lab 1.1.1 smoke OK` |
| Build Identity phase 4C.2 (runtime module) | OK |
| Synthetic cohort create → freeze → blind save → reveal → compare → export → integrity | OK |
| Reopen store / hash persistence | OK |
| Owner corpus not embedded | OK |

**Owner visual QA still required** (live Viewer/Diagnostics candidate-hide sweep, Sequence Follow live, Cancel responsiveness, second-review UX). See `docs/PHASE4C2_OWNER_QA.md`.

## Scientific non-claims

- Corpus is **not** ground truth  
- Phase does **not** scientifically validate the candidate engine  
- No accuracy/F1/etc.  
- Geometry reviews ≠ morphology labels  
- Production RuleEngine remains unwired  
- Candidate rules/thresholds unchanged  

## Git

- **No commit**  
- **No push**  
- Owner approves visual/workflow QA before any later commit/push
