# Phase 4C.2a — Acceptance Report

**Build Identity:** `4C.2a`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Git:** no commit, no push  
**Owner visual QA:** not claimed PASS

## Owner findings (4C.2)

1. Expert Review Corpus page stayed English while app language was Russian.  
2. With two MAT files and 2014-10-15 active, Viewer/cache behaved as if active was unavailable; Batch processed 2013-01-01 until deactivate/reactivate.  
3. Corpus had no real project data / no Add-to-Corpus actions.  
4. “Create pilot cohort” created `pilot_frame_*` placeholders.  
5. Running Diagnostics did not add corpus items (correct that it should not auto-add; missing explicit action).  
6. Review workspace showed instruction placeholder instead of the ionogram.  
7. Comparison/Summary empty because no real items.

## Exact root causes (verified in code)

### Active source / Batch (primary)

**Code path:** `MainWindow._batch_start` previously passed `self.session.selected_mats` to `batch_analyze`, which iterates inventory in registration order. Active source was ignored for which MAT files run.

**Stale state:** UI/cards used `session.active_mat` / `ActiveSourceSnapshot`, while Batch used full inventory. Preview showed inventory count, not active filename.

### Restore fallback (contributing)

**Code path:** `AppSession.restore_inventory_from_project` silently activated the first existing inventory path when saved `active_source_path` was missing — could rebind the wrong MAT after path issues.

### Cache / path identity (contributing)

**Code path:** `AppSession.ensure_store` reused FrameStore only when `frame_store.source_path == active_mat.resolve()`, while snapshots used `paths_equal` without resolve. Relative vs absolute / normcase mismatches forced rebuilds and empty SHA → apparent “missing” cache for the active file.

### Corpus placeholders

**Code path:** `ExpertReviewCorpusPage._create_pilot_cohort` always built synthetic `pilot_frame_{i}.mat` with fake SHAs and never read `session.active_mat` / inventory.

### Localization

Corpus UI used hard-coded English strings; did not call `i18n.t` / `retranslate` for tabs, buttons, combo labels.

### Review ionogram

Review tab used a text placeholder instructing the owner to open Viewer/Diagnostics.

## Fixes delivered

### Authoritative active-source contract

New module `ui/active_source_authority.py`:

- `AuthoritativeActiveSource` (inventory id, path, SHA, generation, revision, availability)
- `authoritative_active_source(session)`
- `batch_mats_from_active(session)` — **active only; never first-inventory fallback**
- `freeze_batch_source_snapshot` for mid-run isolation
- `active_source_label` RU/EN
- `resolve_project_source_path` for project-relative restore

### Session / Batch / ensure_store

- Restore: missing saved active → clear active, keep inventory (no silent first MAT)
- `ensure_store`: project-path resolve + `paths_equal` reuse
- Batch preview/start: active source only; block with explicit message if unavailable / not selected; freeze snapshot for the run

### Production corpus real data

- Removed production `pilot_frame_*` creation path
- Real wizard: active source + frame range preview → confirm → create
- `add_items_to_draft`, zero-item freeze rejection
- `project_items.py` builds SHA/frame identities from active source
- Viewer: «Добавить текущий кадр в корпус»
- Diagnostics: «Добавить кадр в корпус» / «Добавить выбранные кадры в корпус»
- Diagnostics alone still does **not** auto-add

### Embedded Review ionogram

`ReviewIonogramView` loads exact SHA/frame via FrameStore; identity mismatch blocks blind save; candidate stays hidden.

### Live RU/EN

Full `expert_corpus.*` i18n keys; page `retranslate()` updates tabs, fields, combo display labels, empty states; EN↔RU without restart.

## Scientific contracts preserved

Geometry `iml2-0.2.0`, candidate `iml-morph-candidate-0.1.1`, ruleset `0.1.0`, schemas 2/2/1…, shadow-only, RuleEngine unwired, Sequence Follow unchanged, append-only / blind-lock order unchanged. No training/tuning/validation claims.

## Files changed (principal)

- `ui/active_source_authority.py` (new)
- `ui/review_ionogram_view.py` (new)
- `ui/expert_review_corpus_page.py` (rewrite)
- `ui/session.py`, `ui/main_window.py`, `ui/feature_diagnostics_page.py`, `ui/build_identity.py`
- `morphology_review_corpus/project_items.py`, `store.py` (add/freeze), `exports.py`, `models.py`
- `i18n/en.json`, `i18n/ru.json`
- Tests: `test_phase4c2a_*`, updated 4C.2 / 4C.1e build-identity pins
- Docs: this report; `PHASE4C2_OWNER_QA.md` updated

## Test results

### Focused 4C.2a + 4C.2

```
python -m pytest tests/test_phase4c2a_* tests/test_phase4c2_*.py -q
34 passed
```

### Related suites

```
tests/test_phase4b2c_active_source.py
tests/test_phase4b2d_active_source_ux.py
tests/test_language_ux.py
tests/test_phase4c1e2_sequence_follow.py
→ 85 passed
```

### Full pytest

```
python -m pytest tests -q
557 passed in ~336s
```

### Warning audit (honest)

| Command | Result |
|---------|--------|
| `python -m pytest tests -q` | 557 passed; default filter — no warning summary line |
| `python -m pytest` | same suite, exit 0 |
| `python -W default -m pytest tests/test_phase4c2a_* … -q` | **34 passed, 34 warnings** — all `ResourceWarning: unclosed database` from project SQLite/yaml teardown in UI/session fixtures (pre-existing pattern). **No new DeprecationWarning / scientific warnings** introduced by 4C.2a logic. Not globally suppressed. |

## Validators

| Check | Result |
|-------|--------|
| Registry | 93/93 |
| Synthetic Geometry | 17/17 |
| V2 shadow | OK |
| Morphology candidate shadow | OK |
| Morphology review corpus | OK |
| i18n | OK |
| docs | passed |
| repository hygiene | 0 violations |

## Packaging

- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`
- Build Identity phase: **4C.2a**
- SHA-256: **`24FD766F5B84738FBAC888BE6C45D3F821CEB677DF7591E57DC1C19227F97909`**
- Prior SHA: `8DAF2F0BC9FD2D8EAFA8D9047F709003439AF8AB68B1B3F6457710C2ACAB6815` (differs ✓)
- `--smoke-test`: OK  
- No owner MAT/corpus embedded in package

## Packaged two-source smoke (automated)

Synthetic fixtures only: register A+B → activate B → Batch/Viewer/ensure_store resolve B only → real cohort from B (no `pilot_frame_*`) → freeze → blind → reveal → export → integrity OK → reopen preserves active B + manifest hash.

**Owner visual QA still required** — see `docs/PHASE4C2_OWNER_QA.md`. This report does **not** claim owner QA PASS.

## Scientific non-claims

- Not ground truth; not scientifically validated  
- No accuracy/F1  
- Geometry reviews ≠ morphology labels  
- No commit / no push  
