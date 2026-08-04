# PHASE 4C.1b Acceptance Report

**Phase:** Packaged QA Closure — Localized Evidence View, Remaining Enum Cleanup, Fragmentation Ledger Verification, and Review Supersession  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.0` (thresholds unchanged)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (not tuned)  
**Mode:** shadow-only  
**Date:** 2026-08-04  
**Prior EXE (owner-tested 4C.1a):** `DA8B2DA80EDCE6ADA51E9B1D872E6DDEB893D625C6E57C4CBEC1CCC5326919E2`

## Verdict

Owner remaining items from packaged QA are addressed in code and automated tests: normal RU/EN explanations no longer leak canonical abstention enums; the Feature Diagnostics page title localizes; Evidence opens a localized ledger table (canonical JSON under More…); real V2 exports confirm the split fragmentation/oversegmentation ledger; cached-return status states that no computation was performed; geometry-review audits report files / logical frames / current / superseded separately.

## Enum-localization correction

Canonical abstention tokens are mapped in `presentation.ABSTENTION_LABELS` and used by:

- `format_abstention_sentence` / `localized_concise_explanation`
- `format_panel_text` (final strip via `CANONICAL_ABSTENTION_TOKENS`)
- engine `_build_explanations` (stored `human_explanation_ru` / `_en`)

Example blank-frame / no-trace panel (RU):

> Оценка невозможна: допустимый ионосферный след отсутствует.

`no_valid_ionospheric_trace` remains only in technical/JSON/cache/logs.  
`contains_canonical_abstention_enum()` rejects leaked tokens in the normal panel.

## Page-title localization

| Surface | RU | EN |
|---|---|---|
| Nav / page title (`nav.feature_diagnostics`) | Диагностика следа и геометрии | Trace and Geometry Diagnostics |
| Candidate panel | Предварительный кандидат морфологии | Provisional morphology candidate |
| Evidence dialog | Журнал доказательств | Evidence ledger |
| Primary Evidence button | Доказательства | Evidence |

`MainWindow._retranslate_chrome` and `FeatureDiagnosticsPage.retranslate_ui` both refresh `title_feature_diagnostics`. Language switch remains chrome/visible-only (no scientific rebuild).

## Localized evidence view

Primary **Evidence** / **Доказательства** opens a `QTableWidget` with columns:

| RU | EN |
|---|---|
| Правило | Rule |
| Признак | Feature |
| Измеренное значение | Measured value |
| Единица | Unit |
| Условие | Condition |
| Результат | Result |
| Влияние | Effect |
| Сила | Strength |
| Объяснение | Explanation |

User-facing enums (validity, support direction, strength, booleans) are localized.  
Canonical JSON: **More… → Copy / Export evidence JSON** (+ Technical provenance).  
Localized rows and canonical ledger share the same `ledger_hash`.

### Localized evidence excerpt (real export, frame 421 / 2014-10-15)

Source: `docs/_phase4b3_iml2-0.2.0_diagnostics/Am_all_2014-10-15/frame_0421/features.json`  
`ledger_hash`: `ad9e6e811c0a2090ff240fa8d94cda014a5a64defa98d332895e84871decd8d7`

| Правило | Признак | Измеренное значение | Единица | Условие | Результат | Влияние | Сила | Объяснение |
|---|---|---|---|---|---|---|---|---|
| gate_oversegmentation_flag | v2_oversegmentation_suspected | нет | flag | да | Допустимо | Нейтрально | нет | Флаг пересегментации ложен; сам по себе не блокирует. |
| gate_fragmentation_score | v2_fragmentation_score | 3.6666666666666665 | score | 0.75 | Допустимо | Блокирует | сильная | Оценка фрагментации … ≥ 0.75; блокирует надёжную морфологию. |

*(Owner UI screenshot of the dialog is the packaged-EXE check; table above is the same localized ledger content.)*

Machine-readable snapshot: `docs/_phase4c1b_qa_snapshot.json`.

## Fragmentation ledger verification (real V2)

Reproduced from frozen diagnostics exports (not invented):

| Export | Candidate | Abstention | Overseg flag | Frag score | Trigger |
|---|---|---|---|---:|---|
| Am_all_2014-10-15 / frame 421 | indeterminate | `severe_fragmentation` | false → neutral | 3.667 (≥ 0.75) blocks | fragmentation only |
| Am_all_2014-10-15 / frame 1431 | indeterminate | `severe_fragmentation` | false → neutral | 2.0 (≥ 0.75) blocks | fragmentation only |

Packaged helper: **More… → Copy fragmentation gate rows** (`fragmentation_gate_rows`).

Note: older eight-frame audit row for 2014-09-25 frame 421 may still show `no_valid_ionospheric_trace` for that export identity — independent of the 2014-10-15 fragmentation proof above.

## Cached-return status wording

When both V2 and candidate hydrate from cache:

- RU: `V2 загружен из кэша; кандидат загружен из кэша.` / `Расчёт не выполнялся.`
- EN: `V2 loaded from cache; candidate loaded from cache.` / `No computation was performed.`

Distinguished from V2 recalculated, candidate newly evaluated, V2 cache without candidate, and legacy incomplete V2.

## Geometry-review logical counts / supersession

Logical identity: `(review_kind, source_sha256, frame_index, feature_version, diagnostics_cache_id)`.

Behaviour: update-in-place current file per identity; older files retained as superseded history (`load_geometry_review_corpus`).

### Owner workspace corpus (`IML_Project_65064ddf202b`)

| Metric | Count |
|---|---:|
| Review files found | 9 |
| Logical reviewed frames (unique source_sha + frame among current) | 9 |
| Current reviews (unique full identity) | 9 |
| Superseded reviews | 0 |

**Clarification:** frame index 421 appears twice with **different** `source_sha256` values — two source identities, not one superseded pair. Therefore this corpus is **not** “8 logical + 1 superseded.” Metrics API is ready so a true double-save of the same identity will not be counted as two independent frames. Synthetic tests prove supersession grouping (newest current; older history; logical frames &lt; files).

## Tests and validators

| Check | Result |
|---|---|
| `tests/test_phase4c1b_presentation_and_reviews.py` | added |
| Full `pytest tests/` | **415 passed** |
| `validate_morphology_candidate_shadow.py` | OK (extended for 4C.1b) |
| `validate_feature_shadow_mode.py` | OK |
| `validate_i18n.py` / `validate_docs.py` | OK |
| `validate_feature_registry_v2.py` | OK |
| `validate_synthetic_geometry_v2.py` | OK |
| README / version consistency | OK |
| `check_repository_hygiene.py` | pre-existing failures only (zip/large file, absolute paths in older docs, unrelated) |

Covered assertions include: no canonical enums in RU panel; no raw dict dumps in EN; page title RU/EN; Evidence table primary path; JSON under More…; shared ledger hash; false overseg non-blocking; frag score numeric + threshold; exact trigger; review supersession; cached-return wording; candidate cache hit with `v2_request_count == 0`; RuleEngine isolation; Cancel / language-switch suites remain green.

## Scientific non-claims

- No scientific classification validation  
- No accuracy / sensitivity / specificity / F1  
- Geometry reviews ≠ morphology ground truth  
- Thresholds / ruleset unchanged and unvalidated  
- V2 + candidate remain shadow-only  
- Production RuleEngine unwired  
- Phase 4C.2 not started  

## Remaining blockers

- Owner packaged EXE QA checklist (below)  
- True supersession on the live corpus only appears after a second save of the **same** logical identity  
- Do not begin Phase 4C.2 / production enablement  

## Packaged EXE

| Field | Value |
|---|---|
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| SHA-256 | `368EE21073D1BECDB2BAFEF6CAF86FBF7F95A821EAA5AD84ACF91F82998AECD4` |

### Owner QA checklist

1. RU page title is **Диагностика следа и геометрии**  
2. Blank-frame explanation contains no `no_valid_ionospheric_trace`  
3. Evidence opens as localized table  
4. Raw JSON remains under More…  
5. Fragmentation frame shows numeric fragmentation score  
6. False oversegmentation flag is not marked as the blocker  
7. Cached return says no calculation was performed  
8. Review overview reports files vs logical / current / superseded (expect 9/9/9/0 on current corpus; superseded &gt; 0 only when identities match)  
9. RU/EN switch remains fast  
10. Cancel and sequence remain stable  

## Git

- **No commit**  
- **No push**  
