# Phase 4A.1 Compatibility Note (Feature Pipeline V2)

Phase 4A.1 normalizes `SIGNAL_CONTRACTS.yaml` fields:

| Removed / discouraged | Replacement |
| --- | --- |
| `accepted_shape_variants` (mixed shapes + note dicts) | `accepted_shapes`, `shape_constraints`, `accepted_dtypes`, `optional_presence`, `verification_evidence` |

## Minimum Phase 4B impact

- Phase 4B continues to use contract ID `kfu_amp_all_v1` as a string.
- Phase 4B does **not** read `accepted_shape_variants`.
- Loader `load_signal_contracts()` still accepts a legacy file that only has `accepted_shape_variants` by projecting numeric shapes into `accepted_shapes` (compat shim).
- Feature Pipeline V2 remains **disabled by default** and was not redesigned, tuned, or enabled in 4A.1.
- Centerline over-segmentation is **out of scope** (deferred to Phase 4B.1).

## Phase 4A.1b follow-up

- `FrameStore.get_frame` now delegates to `extract_frame_consistent` (canonical extraction).
- Formula summary adds `observational_definitions` (F002 no longer under exact physical formulas).
- Feature Pipeline V2 remains disabled; centerline tuning still deferred to Phase 4B.1.

No morphology RuleEngine thresholds were changed.
