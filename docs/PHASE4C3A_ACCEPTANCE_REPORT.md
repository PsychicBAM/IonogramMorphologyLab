# Phase 4C.3a — Acceptance Report

**Build Identity:** `4C.3a`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.3):** `CA08E26476EEAE37AD20753727E5E682F1CA72A57F50A8A5B6AC6D76778CCCC2`  
**New EXE SHA-256:** `5E2F594B1BE173F9179C62F577C0C7C3CA23B6C42485A8131CD36FD3E4DFB48D`

**Verification mode:** time-constrained targeted verification.  
**Full pytest suite deferred** until the final release gate before commit/push.  
Do **not** claim complete regression verification.  
Owner visual QA is **not** claimed PASS.

---

## Owner findings

1. Campaign Creation Wizard was English while the app UI was Russian.  
2. Sources step required optional second-source SHA-256 and display name.  
3. Owner should never need to type SHA-256.  
4. Wizard accepted arbitrary display names (e.g. “abdalla”) with non-inventory SHAs.  
5. Review then blocked with «Несовпадение SHA источника — отображение заблокировано.»  
6. Preview could not prove real registered source/frame identity.  
7. Campaign page showed «Сначала откройте проект.» despite an open project/active source.  
8. Authoritative active source was not clearly selected/shown.

---

## Exact source-selection root cause

| Defect | Cause |
|--------|--------|
| Manual SHA/display fields | Wizard `_extra_source_sha` / `_extra_source_name` accepted free text and built `SourceScopeEntry` without inventory check |
| Invalid review hydration | Item `source_sha256` did not match any registered MAT / active store SHA |
| English wizard | Step titles and field labels hardcoded in English |
| “Open project first” | Campaign page did not subscribe to `project_changed` / `active_mat_changed` / `inventory_changed` and did not refresh on `showEvent` |

---

## Why manual SHA was removed

SHA-256 is an internal immutable identity derived from registered project sources. The normal wizard must never invent or type it. Manual/external identity belongs only under **Advanced → Import Manifest** with strict inventory matching.

---

## Authoritative inventory picker

- Table from `list_registered_project_sources(session)`  
- Columns: Use / Source / Date / Status / Source SHA (short) / Data range  
- Full SHA in tooltip  
- Default: active source selected — «Активный источник — выбран автоматически»  
- Actions: Active only / Select available / Clear selection  
- No first-MAT fallback  
- Multi-source via checkboxes (not a single “optional second source” pair)

---

## Project-context refresh

Campaign page now:

- resolves `session.project` live (no page-local project cache)  
- connects `project_changed`, `active_mat_changed`, `inventory_changed`  
- refreshes on `showEvent`  
- shows authoritative active-source label  

---

## Prevention validation

`create_campaign(..., session=session)` normalizes and validates every source against the project inventory. Arbitrary display names and unregistered SHAs raise `CampaignError`.

---

## Invalid campaign repair

**Repair Source Mapping** / «Исправить привязку источников»:

1. Inspect invalid `source_scope` rows  
2. Owner maps to registered inventory SHAs  
3. Creates a new corrected campaign + linked cohort  
4. Archives original; does **not** mutate frozen original cohort manifests  
5. Does not copy invalid review records  

---

## RU/EN wizard

Live i18n for step titles, columns, buttons (Next/Back/Cancel/Create), sampling, reviewers, preview, validation. Dark readable contrast stylesheet applied to the wizard.

---

## Focused tests

| Suite | Result |
|-------|--------|
| `test_phase4c3a_*` | **10 passed** |
| Campaign + high-risk set | **40 passed** |
| Warning audit (`-W default` on 4C.3a) | No Phase-4C.3a-introduced ResourceWarnings (only env pytest-asyncio deprecation) |

**Full pytest:** deferred.

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

## Static regression audit

| Check | Result |
|-------|--------|
| No normal editable source SHA input | OK |
| No first registered MAT fallback | OK |
| No arbitrary source alias accepted (with session) | OK |
| No stale project object on Campaign page | OK |
| Identity gate still blocks unregistered SHA | OK |
| Candidate leakage avoided in picker/preview | OK |
| Current-state progress unchanged | OK |
| No production RuleEngine wiring | OK |
| No unsupported scientific claims | OK |

---

## Build

- Build Identity: `4C.3a`  
- Scientific versions unchanged; shadow-only; `scientifically_validated = false`  
- EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
- SHA-256: `5E2F594B1BE173F9179C62F577C0C7C3CA23B6C42485A8131CD36FD3E4DFB48D` (≠ 4C.3)

---

## Packaged smoke (synthetic)

1. Two registered synthetic MATs; source B active  
2. Inventory lists B as active default  
3. Select A+B via checkboxes; no manual SHA fields  
4. Create campaign with real `.mat` names and SHAs  
5. Invalid legacy “abdalla” campaign repaired → archived original + corrected campaign  

---

## Explicit deferral

**Targeted verification passed; full-suite regression is deferred due to the owner’s time-constrained development window.**

Full `python -m pytest` remains mandatory before commit/push.

---

## Git

- **No commit**  
- **No push**  
- Staged: 0  
