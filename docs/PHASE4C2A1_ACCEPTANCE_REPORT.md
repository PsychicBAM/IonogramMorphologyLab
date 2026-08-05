# Phase 4C.2a.1 — Acceptance Report

**Build Identity:** `4C.2a.1`  
**Mode:** shadow-only  
**Date:** 2026-08-05  
**Prior EXE SHA-256 (4C.2a):** `24FD766F5B84738FBAC888BE6C45D3F821CEB677DF7591E57DC1C19227F97909`  
**New EXE SHA-256:** `D764CBCFD66ED8F0EEB1D004FB70C52449F3D0B85D08C35CB7F68B098E295690`  

Owner visual QA is **not** claimed PASS. Automated domain/UI tests and validators are green; packaged GUI smoke steps that require interactive visual confirmation remain for the owner.

---

## Owner findings addressed

| Finding | Resolution |
|---------|------------|
| Frame can be added to draft but no matching remove | Paired **Add current Viewer frame** / **Remove current Viewer frame from draft** (exact SHA+frame) |
| After freeze, no way to continue editing | **Create editable revision** — new draft child; parent frozen manifest untouched |
| Direct unfreeze would break immutability | **Rejected by design** — no `frozen → draft` transition; domain raises on mutation |
| Legacy `pilot_frame_*` cohorts look real | Detected, badged, hidden by default (`Show legacy synthetic`) |
| RU still English: freeze gate, Yes/No, raw meta | Localized dialogs + metadata labels; custom buttons |

---

## Why direct unfreeze was rejected

A frozen cohort is a scientific, hash-bound item list. In-place unfreeze would allow silent mutation of a published manifest identity and break append-only review trust. Editable work continues only via a **new cohort_id** revision that copies item identities/protocol and never copies reviews, comparisons, or adjudications.

---

## Draft editing actions

- Add / remove current Viewer frame (exact `source_sha256` + `frame_index`)
- Remove selected queue items (with preview + confirmation + audit)
- Clear draft (keeps protocol; batch audit)
- Delete draft (only draft; blocked if reviews/comparisons/adjudications exist)
- Freeze rejects zero items; frozen rejects add/remove/clear/delete at UI and domain

Exact remove semantics: identity key is `(sha256.lower(), frame_index)` — never display name alone. Remove disabled when current Viewer frame is absent from the draft.

---

## Revision workflow

1. Parent remains frozen and byte-stable for `cohort_manifest.json`
2. Child gets new `cohort_id`, `parent_cohort_id`, `revision_number`, required `revision_reason`, `created_from_manifest_hash`, `created_from_protocol_hash`
3. Protocol + item identities/order copied; reviews/comparisons/adjudications not copied
4. Child starts as draft; new manifest hash when later frozen
5. Audit events on parent (`cohort_revision_spawned`) and child (`cohort_revision_created`)

---

## Archive behaviour

Workspace-only visibility via `{project}/review_dataset/morphology_corpora/_workspace.json`. Does **not** alter scientific hashes or frozen/draft state. Hidden by default; revealed with **Show archived**. Restore returns to list without unfreezing.

---

## Legacy synthetic handling

Markers: `pilot_frame_*` names, `pilot_inv_*`, synthetic/developer inclusion reasons, weak inventory + padded fake SHA. Not deleted silently. Hidden by default; integrity reports legacy status via `collect_info` without failing real corpora. Word “pilot” alone does not classify a real corpus as synthetic.

---

## Localization fixes

- RU: «Перед сохранением слепой оценки корпус необходимо зафиксировать.»
- Freeze dialog buttons: «Зафиксировать» / «Отмена» (no OS Yes/No)
- Metadata: ID корпуса, Зафиксирован, Черновик, Элементы, Метод выборки, Ручная/Случайная, Ожидает оценки, ревизия/родитель, хеши
- Seed → «Зерно случайной выборки»
- Runtime EN↔RU retranslate covers badges, buttons, dialogs, queue, info panel
- Blind-on-draft offers «Перейти к корпусу» / «Отмена» and preserves unsaved form values

---

## Tests

- `tests/test_phase4c2a1_draft_editing.py`
- `tests/test_phase4c2a1_revision_archive_legacy.py`
- `tests/test_phase4c2a1_localization.py`
- Updated 4C.2 / 4C.2a UI tests for custom `_ask` dialogs
- Build identity pins → `4C.2a.1`

**Results:**

| Suite | Result |
|-------|--------|
| `test_phase4c2a1_*` | 9 passed |
| All relevant 4C.2 suites | 43 passed |
| `python -m pytest tests -q` | **566 passed** |

---

## Warning audit

Command: `python -W default -m pytest tests/test_phase4c2*.py …` (4C.2 / 4C.2a / 4C.2a.1 files)

- **43 passed, 42 warnings**
- All 42 are pre-existing `ResourceWarning: unclosed database` from AppSession/sqlite teardown during YAML GC paths — **not newly introduced** by draft/revision logic
- Not globally suppressed
- Additional `PytestDeprecationWarning` from unset `asyncio_default_fixture_loop_scope` (pytest-asyncio config; unrelated)

---

## Validators / hygiene

| Check | Result |
|-------|--------|
| Feature registry | 93/93 |
| Synthetic geometry | 17/17 |
| Feature shadow | OK |
| Morphology candidate shadow | OK |
| Morphology review corpus | OK |
| i18n | OK |
| docs | passed |
| repository hygiene | 0 violations |

Scientific versions unchanged: geometry `iml2-0.2.0`, candidate `iml-morph-candidate-0.1.1`, ruleset `iml-morph-candidate-rules 0.1.0`, review schemas 1.

---

## Packaged smoke

EXE: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`  
SHA-256: `D764CBCFD66ED8F0EEB1D004FB70C52449F3D0B85D08C35CB7F68B098E295690` (≠ prior)

Automated domain smoke covering create → add → remove → re-add → remove selected → freeze → mutation reject → editable revision → child mutate → parent unchanged → freeze child → integrity both → archive/show flags → RU string checks: **OK**.

Interactive owner checks still required for: embedded ionogram visual, candidate hide-before-lock UI, RU dialog appearance, no Not Responding under load.

---

## Git

- **No commit**
- **No push**
- Phase 4C.2b Rapid Review Table / Structured Comment Builder **not started**

---

## Owner QA still required

Do not treat this report as visual/workflow PASS. Use `docs/PHASE4C2_OWNER_QA.md` (updated for 4C.2a.1).
