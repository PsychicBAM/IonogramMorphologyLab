# PHASE4C1 Feature Input Audit

Geometry Feature Pipeline version: **iml2-0.2.0** (93 registered features).
Morphology candidate engine: **iml-morph-candidate-0.1.0** (shadow-only).

## Method

- Inventory uses canonical IDs from `knowledge_base/FEATURE_REGISTRY_V2.yaml`.
- Candidate engine consumes registry IDs / typed V2 serializable results only.
- No UI-label parsing, no direct pixel reads inside the candidate engine,
  no hidden duplicate measurements bypassing Feature Registry V2.

## Candidate-relevant features

| feature ID | name EN | name RU | unit | expected range | missing policy | level | H | V | quality | interference | ambiguity | temporal/mixed | suitable | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `v2_accepted_support_above_floor_fraction` | accepted support above floor fraction | accepted support above floor fraction | fraction | 0..1 | invalid_not_zero | frame |  |  | Y |  |  |  | yes | Non-floor accepted support gate. |
| `v2_branch_count` | branch count | branch count | count | None | invalid_not_zero | frame |  |  | Y |  |  |  | no (rejected/deferred) | Secondary; prefer consolidated count. |
| `v2_coexistence_fraction` | coexistence fraction | coexistence fraction | fraction | 0..1 | invalid_not_zero | frame |  |  |  |  |  | Y | yes | Spatial coexistence fraction for mixed. |
| `v2_coexistence_score` | coexistence score | coexistence score | score | 0..1 | invalid_not_zero | frame |  |  |  |  |  | Y | yes | Independent coexistence score for mixed. |
| `v2_consolidated_branch_count` | consolidated branch count | consolidated branch count | count | None | invalid_not_zero | frame |  |  | Y |  |  |  | yes | Branch context / oversegmentation signal. |
| `v2_fixed_horizontal_axis_width_bins` | fixed horizontal axis width bins | fixed horizontal axis width bins | bins | 0..400 | invalid_not_zero | frame | Y |  |  |  |  |  | no (rejected/deferred) | Aggregate; elevated fraction preferred for coverage. |
| `v2_fixed_vertical_axis_width_bins` | fixed vertical axis width bins | fixed vertical axis width bins | bins | 0..400 | invalid_not_zero | frame |  | Y |  |  |  |  | no (rejected/deferred) | Aggregate; elevated fraction preferred. |
| `v2_floor_clutter_burden` | floor clutter burden | floor clutter burden | fraction | 0..1 | invalid_not_zero | frame |  |  |  | Y |  |  | yes | Reject V-as-range when floor dominates. |
| `v2_fragmentation_score` | fragmentation score | fragmentation score | ratio | 0..1000000000000.0 | invalid_not_zero | frame |  |  |  |  | Y |  | yes | Severe fragmentation → abstention. |
| `v2_full_height_stripe_burden` | full height stripe burden | full height stripe burden | fraction | 0..1 | invalid_not_zero | frame |  |  |  | Y |  |  | yes | Reject V-as-range when full-height stripes dominate. |
| `v2_horizontal_axis_width_applicable_fraction` | horizontal axis width applicable fraction | horizontal axis width applicable fraction | fraction | 0..1 | invalid_not_zero | frame | Y |  |  |  |  |  | yes | Fraction of positions where H axis is applicable. |
| `v2_horizontal_contiguous_broadening_length` | horizontal contiguous broadening length | horizontal contiguous broadening length | samples | 0..400 | invalid_not_zero | frame | Y |  |  |  |  |  | yes | Persistence/contiguity for H support. |
| `v2_horizontal_width_elevated_fraction` | horizontal width elevated fraction | horizontal width elevated fraction | fraction | 0..1 | invalid_not_zero | frame | Y |  |  |  |  |  | yes | Primary H coverage evidence (not single max). |
| `v2_interference_level` | interference level | interference level | categorical | [] | invalid_not_zero | frame |  |  |  | Y |  |  | yes | Separate interference axis; blocking → not_assessable. |
| `v2_interference_stripe_density` | interference stripe density | interference stripe density | fraction | 0..1 | invalid_not_zero | frame |  |  |  | Y |  |  | no (rejected/deferred) | Supporting; burden/level preferred. |
| `v2_interference_trace_overlap` | interference trace overlap | interference trace overlap | fraction | 0..1 | invalid_not_zero | frame |  |  |  | Y |  |  | yes | Horizontal/overlap interference context. |
| `v2_local_horizontal_width_max` | local horizontal width max | local horizontal width max | bins | 0..400 | invalid_not_zero | frame | Y |  |  |  |  |  | no (rejected/deferred) | Rejected as sole rule input (single max). |
| `v2_local_vertical_width_max` | local vertical width max | local vertical width max | bins | 0..400 | invalid_not_zero | frame |  | Y |  |  |  |  | no (rejected/deferred) | Rejected as sole rule input (single max). |
| `v2_median_local_horizontal_width_bins` | median local horizontal width bins | median local horizontal width bins | bins | 0..400 | invalid_not_zero | frame | Y |  |  |  |  |  | yes | Robust H width central tendency. |
| `v2_median_local_vertical_width_bins` | median local vertical width bins | median local vertical width bins | bins | 0..400 | invalid_not_zero | frame |  | Y |  |  |  |  | yes | Robust V width central tendency. |
| `v2_multiple_reflection_possibility` | multiple reflection possibility | multiple reflection possibility | flag | 0..1 | invalid_not_zero | frame |  |  |  |  | Y |  | yes | Suppress automatic frequency candidate. |
| `v2_oversegmentation_suspected` | oversegmentation suspected | oversegmentation suspected | flag | 0..1 | invalid_not_zero | frame |  |  |  |  | Y |  | yes | Oversegmentation gate → abstention. |
| `v2_ox_ambiguity_possibility` | ox ambiguity possibility | ox ambiguity possibility | flag | 0..1 | invalid_not_zero | frame |  |  |  |  | Y |  | yes | Ambiguity warning flag. |
| `v2_quality_status` | quality status | quality status | categorical | [] | invalid_not_zero | frame |  |  | Y |  |  |  | yes | Primary quality gate before morphology rules. |
| `v2_temporal_branch_persistence` | temporal branch persistence | temporal branch persistence | dimensionless | 0..1000000.0 | invalid_not_zero | frame |  |  |  |  |  | Y | no (rejected/deferred) | Eligible; not sole decision input in 0.1.0. |
| `v2_temporal_interference_persistence` | temporal interference persistence | temporal interference persistence | dimensionless | 0..1000000.0 | invalid_not_zero | frame |  |  |  |  |  | Y | no (rejected/deferred) | Eligible; interference remains separate axis. |
| `v2_temporal_width_persistence` | temporal width persistence | temporal width persistence | dimensionless | 0..1000000.0 | invalid_not_zero | frame |  |  |  |  |  | Y | no (rejected/deferred) | Future temporal layer; 0.1.0 uses TemporalContext object. |
| `v2_trace_continuity` | trace continuity | trace continuity | fraction | 0..1 | invalid_not_zero | frame |  |  | Y |  |  |  | no (rejected/deferred) | Supporting continuity context. |
| `v2_trace_pixel_fraction` | trace pixel fraction | trace pixel fraction | fraction | 0..1 | invalid_not_zero | frame |  |  | Y |  |  |  | yes | Trace presence / blank-frame abstention. |
| `v2_true_slope_compensated_horizontal_residual_bins` | true slope compensated horizontal residual bins | true slope compensated horizontal residual bins | bins | 0..400 | invalid_not_zero | frame | Y |  |  |  |  |  | no (rejected/deferred) | Future refinement; not required in 0.1.0 seed. |
| `v2_usable_trace_fraction_outside_interference` | usable trace fraction outside interference | usable trace fraction outside interference | fraction | 0..1 | invalid_not_zero | frame |  |  | Y |  |  |  | no (rejected/deferred) | Supporting quality context; not sole gate. |
| `v2_vertical_axis_width_applicable_fraction` | vertical axis width applicable fraction | vertical axis width applicable fraction | fraction | 0..1 | invalid_not_zero | frame |  | Y |  |  |  |  | yes | Fraction of positions where V axis is applicable. |
| `v2_vertical_contiguous_broadening_length` | vertical contiguous broadening length | vertical contiguous broadening length | samples | 0..400 | invalid_not_zero | frame |  | Y |  |  |  |  | yes | Persistence/contiguity for V support. |
| `v2_vertical_stripe_count` | vertical stripe count | vertical stripe count | count | 0..400 | invalid_not_zero | frame |  |  |  | Y |  |  | yes | Vertical interference flagging. |
| `v2_vertical_width_elevated_fraction` | vertical width elevated fraction | vertical width elevated fraction | fraction | 0..1 | invalid_not_zero | frame |  | Y |  |  |  |  | yes | Primary V coverage evidence. |
| `v2_width_aggregate_branches_agree` | width aggregate branches agree | width aggregate branches agree | flag | 0..1 | invalid_not_zero | frame |  |  |  |  | Y |  | no (rejected/deferred) | Optional branch-consistency hint. |
| `v2_width_balance_ratio` | width balance ratio | width balance ratio | ratio | 0..1000000000000.0 | invalid_not_zero | frame |  |  |  |  |  | Y | no (rejected/deferred) | Not sufficient for mixed without coexistence. |

## Features not used for candidate rules (registry remainder)

Remaining registered features are geometry/diagnostic only for ruleset 0.1.0.

- `v2_accepted_nonfloor_trace_fraction`
- `v2_along_ridge_support_length_bins`
- `v2_axis_tangent_rejection_count`
- `v2_branch_overlap_rejection_count`
- `v2_branch_parallelism`
- `v2_branch_relative_amplitude`
- `v2_branch_separation_bins`
- `v2_centerline_count`
- `v2_column_background_burden`
- `v2_component_count`
- `v2_consolidation_count`
- `v2_dynamic_range`
- `v2_empty_region_fraction`
- `v2_finite_fraction`
- `v2_floor_candidate_removed_fraction`
- `v2_floor_rejected_component_count`
- `v2_frequency_axis_available`
- `v2_height_axis_available`
- `v2_impulsive_outlier_fraction`
- `v2_inferred_continuation_across_interference`
- `v2_interference_affected_frequency_fraction`
- `v2_interference_stripe_amplitude`
- `v2_interference_stripe_height_persistence`
- `v2_interference_stripe_width`
- `v2_merge_split_locations`
- `v2_multiple_intersection_rejection_count`
- `v2_nonfloor_candidate_retained_fraction`
- `v2_normal_to_ridge_width_bins`
- `v2_normal_width_baseline_residual_bins`
- `v2_overlapping_layer_possibility`
- `v2_potential_trace_interference_overlap`
- `v2_preconsolidation_centerline_count`
- `v2_preexclusion_floor_overlap_fraction`
- `v2_raw_component_count`
- `v2_rejected_component_count`
- `v2_robust_percentile_p1`
- `v2_robust_percentile_p50`
- `v2_robust_percentile_p99`
- `v2_row_background_burden`
- `v2_saturation_fraction`
- `v2_temporal_centerline_displacement`
- `v2_temporal_event_class`
- `v2_temporal_mask_overlap`
- `v2_total_connected_component_count`
- `v2_unresolved_floor_conflict_fraction`
- `v2_unresolved_occluded_fraction`
- `v2_width_aggregate_branches_contributed`
- `v2_width_aggregate_dominant_branch_id`
- `v2_width_connected_support_bins`
- `v2_width_estimator_disagreement`
- `v2_width_estimators_available`
- `v2_width_excluded_count`
- `v2_width_fwhm_bins`
- `v2_width_second_moment_bins`
- `v2_width_valid_count`
- `v2_zero_fraction`

## Explicit rejections

- Do not use `v2_local_*_width_max` alone (single extremum).
- Do not encode `v2_interference_level` as frequency/range/mixed.
- Do not treat high `v2_branch_count` as mixed.
- Do not treat geometry review JSON as morphology ground truth.

## Scientific non-claims

- This audit does not validate classification accuracy.
- Eight geometry reviews are not morphology labels.
