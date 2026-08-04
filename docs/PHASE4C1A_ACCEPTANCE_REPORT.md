# PHASE 4C.1a Acceptance Report

**Phase:** Candidate Cache Hydration, V2 Cache Compatibility, Review Decoupling, Evidence-Ledger Corrections, Candidate UI Polish  
**Geometry:** `iml2-0.2.0` (unchanged)  
**Candidate engine:** `iml-morph-candidate-0.1.0` (unchanged scientific thresholds)  
**Ruleset:** `iml-morph-candidate-rules 0.1.0` (not tuned)  
**Mode:** shadow-only  
**Date:** 2026-08-03  

## Verdict

Owner packaged-QA failures from EXE `D50A5770…` are addressed: candidate cache hydrates on frame return without V2/engine re-run, sequence candidates no longer depend on geometry reviews, legacy incomplete V2 is gated with recalculate UX, fragmentation/oversegmentation ledger entries are separated, and the normal RU/EN panel no longer dumps raw Python structures.

## Candidate-cache root cause

Hydration required an already-loaded `_result_ser` and used a thin `get()` without structured miss reasons. Frame change cleared the morph panel; if V2 summary load failed or was delayed, morph never reloaded. Sequence workers never filled `morph_candidate` at all (owner perception: “appears after geometry review” was coincidental / V2-related, not a real review gate).

## Cache hydration proof

- Exact `MorphologyCandidateCacheKey` built from source SHA, frame, profile, signal contract, feature version, diagnostics cache ID, engine version, ruleset version/hash, temporal signature.
- `MorphologyCandidateCache.lookup()` requires `meta.json` + `result.json` (bare directory ≠ hit).
- Structured miss reasons: `no_index`, `key_mismatch`, `ruleset_changed`, `diagnostics_identity_changed`, `corrupt_result`, `stale_result`, `temporal_signature_changed`.
- Counters: `candidate_cache_lookup_count`, `hit/miss`, `candidate_engine_evaluation_count`, `v2_request_count`, `candidate_loaded_on_frame_activation_count`.
- Acceptance path (unit): cache hit → evaluation unchanged, `v2_request_count == 0`.

## Geometry-review dependency root cause

No hard `if geometry_review` gate existed; sequence simply never computed morph candidates. Fixed via `_enrich_sequence_morph_candidates()` calling `resolve_or_evaluate_candidate()` for every selected frame with a V2 result. Geometry review status is informational only (`geometry_reviewed` / `geometry_unreviewed`).

## V2 compatibility states

`classify_v2_for_candidate()`:

- `compatible_complete`
- `compatible_with_explicit_invalid_features`
- `incompatible_feature_version`
- `incomplete_legacy_cache`
- `corrupt_cache`
- `identity_mismatch`

Incomplete legacy → no candidate evaluation, interference unavailable, RU/EN recalculate-V2 message + button.

## Fragmentation ledger correction

Separate entries:

- `gate_oversegmentation_flag` (`v2_oversegmentation_suspected`) — blocks only when true  
- `gate_fragmentation_score` (`v2_fragmentation_score`) — shows numeric value vs threshold  

Abstention reasons: `oversegmentation_suspected` | `severe_fragmentation` | `both_oversegmentation_and_fragmentation`.

## Localization / UI polish

- Localized panel via `presentation.format_panel_text` (no raw dicts/tuples/enums in normal view).
- Localized evidence ledger columns; JSON via Copy/Export.
- Primary buttons on two rows + More… overflow (provenance, clear cache, export, review folder).
- Full shadow disclaimer shown once at top of panel.

## Corrected eight-frame audit identities

Rebuilt from exact geometry-review JSON under  
`workspaces/IML_Project_65064ddf202b/feature_diagnostics/geometry_reviews/`  
(9 review files found; each listed by `source_sha256`, `frame_index`, `diagnostics_cache_id`, `feature_version`).  
Missing/unresolved exports recorded as `source_identity_unresolved_or_export_missing` — not replaced.  
See `docs/PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md`. No correctness claim.

## Tests / validators

| Check | Result |
|---|---|
| `tests/test_phase4c1a_candidate_hydration.py` | added |
| `tests/test_phase4c1_morphology_candidate.py` | updated ledger assertions |
| Full pytest | **404 passed** |
| Registry / synthetic geometry / shadow / morph / i18n / docs | OK |

## Performance

Candidate evaluate/load remains on compact V2 JSON (ms-scale). Cache hydration does not reopen MAT or rerun V2.

## Scientific non-claims

- No scientific classification validation  
- No accuracy / sensitivity / specificity / F1  
- Geometry reviews ≠ morphology labels  
- Thresholds unchanged / unvalidated  
- V2 + candidate remain shadow-only  
- Production RuleEngine unwired  

## Remaining blockers

- Owner packaged EXE QA checklist (below)  
- Do not begin Phase 4C.2  
- No production enablement  

## Packaged EXE

| Field | Value |
|---|---|
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| SHA-256 | `DA8B2DA80EDCE6ADA51E9B1D872E6DDEB893D625C6E57C4CBEC1CCC5326919E2` |

### Owner QA scenario

1. Fresh V2 on assessable frame → Calculate candidate  
2. Leave frame → return → candidate from cache; V2 does not rerun  
3. Evidence ledger shows numeric fragmentation when it blocks  
4. Legacy incomplete V2 → recalculation message  
5. Recalculate V2 → blank frame `not_assessable` / no valid trace  
6. Sequence without geometry reviews → candidates present  
7. RU/EN + narrow window readable  
8. Save morphology review; Cancel sequence; no Not Responding  

## Git

- **No commit**  
- **No push**  
