# PHASE 4C.1c Acceptance Report

**Phase:** Evidence Identity Integrity, Candidate Cache Schema Invalidation, Lazy Feature Inspector, and Localization Closure  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.1` (thresholds unchanged; schema/contract bump only)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (numerical thresholds unchanged)  
**Mode:** shadow-only  
**Date:** 2026-08-04  
**Prior EXE (owner-tested 4C.1b):** `368EE21073D1BECDB2BAFEF6CAF86FBF7F95A821EAA5AD84ACF91F82998AECD4`

## Verdict

Owner packaged-QA blockers from EXE `368EE210…` are addressed: Evidence is identity-bound and follows (or closes on) frame change; old combined-overseg candidate cache is rejected with candidate-only recalculation messaging; Features tab uses a virtualized model/view; primary Evidence table uses friendly labels and separated data/condition/effect semantics; runtime statuses use message keys reformatted on language switch; review Save is identity-guarded; review corpus overview shows files/logical/current/superseded.

## Stale Evidence root cause

Evidence was a fire-and-forget modal `QDialog.exec()` built once from `_morph_result_dict` with no retained dialog reference and no frame-change sync. After the owner switched frames, a previously opened dialog (or a confused perception when reopening) could not stay bound to the active candidate identity.

## Identity binding architecture

- Immutable identity: `source_sha256`, `frame_index`, `interpreted_time`, `diagnostics_cache_id`, `candidate_result_hash`, `evidence_ledger_hash`, engine/ruleset/schema versions (`evidence_identity_from_result`).
- Non-modal `EvidenceDialog` with compact header (`Источник: … · Кадр: … · Время: …`).
- On frame change: `_clear_candidate_presentation()` bumps `_morph_generation`, clears morph state, closes/marks stale Evidence, closes Review form.
- Default behaviour: Evidence follows the active candidate (`bind_result` on hydrate/calculate).
- Generation guard: late cache callbacks discarded when `_morph_generation` changes.
- Evidence/Review buttons disabled until identity is resolved.

## Candidate-cache schema migration

| Field | Value |
|---|---|
| `candidate_engine_version` | `iml-morph-candidate-0.1.1` |
| `candidate_cache_schema_version` | `2` |
| `evidence_ledger_schema_version` | `2` |
| `candidate_result_contract_version` | `2` |
| `cache_format` | `iml-morph-candidate-cache-v2` |

Schema versions are part of the cache key, `meta.json`, result JSON, and technical provenance.

### Old-cache rejection proof

Legacy `iml-morph-candidate-cache-v1` entries (including combined `gate_oversegmentation`) are probed and classified as `incompatible_candidate_cache_schema` / `incompatible_ledger_schema`. UI message:

> Candidate cache was created by a previous version. Recalculate the candidate only; V2 recalculation is not required.

V2 cache is preserved. Content validation also requires split fragmentation rows when frag abstention reasons apply; hash/source/frame/diagnostics mismatches are structured miss reasons.

## Features tab hotspot profile

Previous path: `_populate_features` rebuilt a `QListWidget` with per-row `feature_entry()` → YAML reload + explanation wiring pressure.

New path (`FeaturesTableModel` + `QTableView` + filter proxy):

| Span | Role |
|---|---|
| `fd.features_tab.activate` | tab switch |
| `fd.features.model_build` | lightweight row records |
| `fd.features.registry_access` | lru-cached registry |
| `fd.features.presentation_build` | localized column data |
| `fd.features.first_paint` | viewport update |

Forbidden on activation: MAT I/O, V2/candidate recalculation, `resizeColumnsToContents` over all rows, full theme/global retranslate. Explanations build only for the selected row.

Unit timing (synthetic ~90+ features): first model load &lt; 0.5 s; warm reload &lt; 0.1 s.

## Full Evidence localization + comparison semantics

Primary table shows friendly labels (e.g. Quality gate / Quality status), localized units/categories, and **no** raw `gate_*` / `v2_*` / Python list dumps by default. Optional “Show technical IDs” + More… JSON/provenance keep canonical values.

Separated columns:

| Concept | Example (frag 0.91 ≥ 0.75) | Example (overseg false) |
|---|---|---|
| Data validity | Данные допустимы | Данные допустимы |
| Condition result | порог превышен | условие не сработало |
| Effect | Блокирует | Нейтрально |

Never: «Результат: Допустимо · Влияние: Блокирует».

## Runtime-status localization

Statuses stored as `StatusMessage(key, args, severity, generation)`. Language switch reformats via `format_status` without V2/MAT/page rebuild. Validator rejects Cyrillic in EN for keys such as `v2_cache_loaded`.

## Review identity guard

Before opening/saving morphology review: `result_hash`, source SHA, frame, diagnostics ID, ruleset hash must match the currently displayed candidate. Mismatch blocks Save and shows identity-changed warning.

## Review corpus overview

**More… → Review corpus overview** / **Обзор проверок** shows:

`files / logical frames / current / superseded`

Current owner workspace expectation: **9 / 9 / 9 / 0**. Informational only.

## Tests and validators

| Check | Result |
|---|---|
| `tests/test_phase4c1c_identity_cache_features.py` | added |
| Full `pytest tests/` | **430 passed** |
| `validate_morphology_candidate_shadow.py` | OK (4C.1c checks) |
| shadow / i18n / docs / registry / synthetic geometry / README / version | OK |

## Packaged profiler

Spans added for Features activate/model/registry/presentation/first_paint and Evidence open/model_update/identity_change. Enable with `IML_PACKAGED_PERF=1`. Owner should confirm Features first/warm and Evidence timings on the new EXE.

## Scientific non-claims

- No scientific classification validation  
- No accuracy metrics  
- Geometry reviews ≠ morphology GT  
- Thresholds / ruleset numbers unchanged  
- V2 + candidate remain shadow-only  
- Production RuleEngine unwired  
- Phase 4C.2 not started  

## Remaining blockers

- Owner packaged EXE QA checklist (below)  
- Packaged Features/Evidence wall-clock confirmation under `IML_PACKAGED_PERF=1`  

## Packaged EXE

| Field | Value |
|---|---|
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| SHA-256 | `3A6A80405BB7C98EE22E33E4E581175AC6ADE089BC7ED225B291AD5120A24ED7` |

### Owner QA checklist

1. Open Evidence on frame 421  
2. Switch to 1431 and 1400 — Evidence follows or closes; identity header updates  
3. Frame identity visible in Evidence  
4. Old candidate cache → candidate-only recalculation message; V2 not recalculated  
5. Features first/warm open timing  
6. Evidence has no raw machine vocabulary by default  
7. Fragmentation row: threshold exceeded  
8. False overseg: condition not met  
9. RU/EN status messages fully localized  
10. Review corpus overview **9 / 9 / 9 / 0**  
11. Save review only for displayed frame  
12. Cancel sequence remains stable  

## Git

- **No commit**  
- **No push**  
