# Phase 4B.3 Acceptance Report

**Phase:** 4B.3 — Orthogonal Width Validity, Branch-Isolated Measurements, Versioned Evidence, and Final Geometry Review  
**Feature version:** `iml2-0.2.0` (was `iml2-0.1.0`)  
**Flag:** `scientific_feature_pipeline_v2_enabled` default **false** (unchanged)  
**Production RuleEngine / Morphology Results:** unchanged  
**Classification accuracy / scientific validation:** not claimed  
**Phase 4C:** not started (blocked pending owner geometry review)  
**Git:** no commit / no push  

## Constraints preserved

| Item | Status |
| --- | --- |
| Phase 4A evidence | Preserved |
| V2 shadow mode | Preserved; default off |
| Production classifications | Unchanged |
| Prior `iml2-0.1.0` evidence | Preserved under `docs/_phase4b1_*` with provenance notes |
| New evidence directories | `docs/_phase4b3_iml2-0.2.0_*` |

## 1. Feature version bump

| Item | Value |
| --- | --- |
| Source constant | `FEATURE_VERSION = "iml2-0.2.0"` |
| Registry root + implementation_version | `iml2-0.2.0` |
| Diagnostic identities / serialized outputs | `iml2-0.2.0` |
| Perf-state resume | Rejects mismatched feature_version |
| Cache invalidation | Old V2 resume state must not mix with 0.2.0; new out dirs used |

## 2–3. Axis applicability and branch-isolated widths

Documented project geometry heuristics (not physical thresholds):

- `ANGLE_NEAR_AXIS_DEG = 30`
- `MULTI_INTERSECTION_MIN_SUPPORT = 3`
- `ALONG_RIDGE_SUPPORT_RATIO = 2.5`

Fixed-axis cuts reject with `axis_tangent_to_trace` when near-tangent; near other-branch overlap rejects with `branch_overlap` / `multiple_intersection`. Widths are computed per branch into `branch_records[].widths`; frame aggregates use only valid branch-local samples.

Registered applicability / rejection features include:

- `v2_horizontal_axis_width_applicable_fraction`
- `v2_vertical_axis_width_applicable_fraction`
- `v2_axis_tangent_rejection_count`
- `v2_multiple_intersection_rejection_count`
- `v2_branch_overlap_rejection_count`

## 4–5. Synthetic fixtures and independence tests

Anisotropic fixtures use orientation-appropriate baselines with known support geometry:

| Case | Result |
| --- | --- |
| Thin horizontal H residual | **Before (4B.2):** ≈ 8.8 bins accepted as width-like; **After:** invalid / `h_applicable=0`, `axis_tangent_rejection_count=160` |
| Frequency-axis-only (steep + X broaden) | H 1.0 → **5.0**; V not treated as frequency broadening |
| Range-axis-only (shallow + Y broaden) | V 2.0 → **5.0**; H inapplicable |
| Both axes (diagonal) | H and V both **4.0** (> thin diagonal 2.0) |
| Two parallel thin branches | count ≥ 2; per-branch V medians **2.0 / 2.0**; aggregate V **2.0** (separation not width) |
| Crossing | ambiguity / multi-branch / rejection path (not silent single-line broadening) |

Strict synthetic suite: **17 / 17 PASS** (`docs/_phase4b3_iml2-0.2.0_synthetic_geometry/`).

## 6. Width aggregation

Per branch: valid H/V samples, invalid reasons, median, uncertainty, contiguous valid regions, applicability fraction.  
Frame aggregate metadata: branches contributed, agreement, dominant branch; unavailable on disagreement. Invalid / overlapping / non-identifiable cuts are not averaged.

## 7. Nonfloor features

`v2_accepted_nonfloor_trace_fraction` retained only as **postcondition check** (metadata `role=postcondition_check_only`).  
Added: `preexclusion_floor_overlap_fraction`, `floor_candidate_removed_fraction`, `nonfloor_candidate_retained_fraction`, `accepted_support_above_floor_fraction`, `unresolved_floor_conflict_fraction`.

## 8. Reproducible performance

Orchestrator: `scripts/run_feature_pipeline_v2_perf_orchestrator.py`  
Stages: (1) cancel-after-30 → (2) resume → (3) completed → (4) second-pass → (5) aggregate `run_manifest.json`.

Checkpoint / resume-state skips are **not** labeled as feature-cache hits (`true_feature_cache_hits = 0` until a V2 result cache exists).  
Evidence dir: `docs/_phase4b3_iml2-0.2.0_fullfile_perf/` (`run_manifest.json` + `fullfile_performance_report.json`).

| Metric | Value |
| --- | ---: |
| Frames completed | 1440 |
| Sum of frame computation times | **2983.1 s** |
| Orchestrator wall (cancel/resume/complete/second) | **~3006 s** (7.0 / 2987.4 / 6.2 / 5.7) |
| Median / p95 s/frame | **1.450 / 4.919** |
| RSS baseline / after Amp_all / peak | **62.4 / 347.3 / 347.3 MB** |
| Resume-state skips (not feature-cache) | 2910 |
| True feature-cache hits | **0** |
| Recomputed frames | 1441 |
| Quality | assessable 703 / degraded 464 / not_assessable 273 |
| Oversegmentation suspected | **533** |

## 9. Regenerated evidence (`iml2-0.2.0`)

| Artifact | Location |
| --- | --- |
| Synthetic geometry | `docs/_phase4b3_iml2-0.2.0_synthetic_geometry/` |
| 18 real diagnostics + contact sheets | `docs/_phase4b3_iml2-0.2.0_diagnostics/` |
| Feature registry | `knowledge_base/FEATURE_REGISTRY_V2.yaml` — **93** features |
| Performance | `docs/_phase4b3_iml2-0.2.0_fullfile_perf/` |

Real packages include per-branch H/V validity (`branch_width_summary.json`), axis applicability counts, and H/V width direction maps.

## 10. Owner geometry review

| Item | Result |
| --- | --- |
| Rows | **18** |
| Completed / pending | **0 / 18** (not auto-marked) |
| New fields | trace mask, floor rejection, interference, centerlines, branch separation, H/V direction, branch overlap, final geometry for rule development, comments |

Phase 4C remains blocked until synthetic H/V independence and parallel-branch tests pass (done), feature version is bumped (done), and owner reviews representative frames (pending).

## 11. Tests and package

| Suite / check | Result |
| --- | --- |
| Phase 4B tests | **30 passed** |
| Full repository suite | **227 passed**, 9 warnings |
| Synthetic geometry | OK 17/17 |
| Registry | OK 93/93 missing=0 |
| Diagnostics | OK |
| Shadow mode | OK |
| Feature parity | OK (14 actual cross-runtime) |
| Production classifications | Unchanged |
| EXE SHA-256 | `8b07b68ea2952312ad8f0840e073471cf7ccc176ded31df10c14cb2bc6140f2b` |

Verification zip: `IML_Phase4B_Verification_Complete.zip` (digest in companion `.sha256`; no source MAT files).

## Residual (not Phase 4C)

Owner visual geometry review is still required. This phase does **not** claim improved morphology accuracy or scientific validation.
