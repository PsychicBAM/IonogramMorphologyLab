# Phase 4B.2 Acceptance Report

**Phase:** 4B.2 — Geometry Validity, Registry Integrity, True Cross-Runtime Parity, and Owner-Review Readiness  
**Feature version:** `iml2-0.1.0`  
**Flag:** `scientific_feature_pipeline_v2_enabled` default **false** (unchanged)  
**Production RuleEngine / Morphology Results:** unchanged  
**Classification accuracy / scientific validation:** not claimed  
**Phase 4C:** not started  
**Git:** no commit / no push in this phase  

## Constraints preserved

| Item | Status |
| --- | --- |
| Phase 4A evidence | Preserved |
| Feature Pipeline V2 shadow mode | Preserved; default off |
| Production classifications | Unchanged |
| V2 not enabled by default | Confirmed |
| Phase 4C | Not started |

## 1. Floor-clutter false traces

Floor components are scored (overlap, fraction in floor mask, continuation above floor, amplitude/ridge above floor) and rejected with reason `floor_component`. Candidate/accepted masks exclude floor clutter; exports include `floor_clutter_mask`, `impulse_mask`, and per-component floor overlap.

| Frame (examples) | Total CC | Preconsol centerlines | Floor rejected | Consolidated | Nonfloor frac | Overseg |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2013-01-01 f421 | 404 | 8 | 6 | 3 | 1.0 | no |
| 2013-01-01 f1440 | 390 | 2 | 6 | 0 | 0.0 | no |
| 2014-10-15 f1431 | 386 | 8 | 10 | 4 | 1.0 | no |

Renames / new counts:

- `v2_total_connected_component_count`
- `v2_preconsolidation_centerline_count` (legacy `v2_raw_component_count` aliases this)
- `v2_floor_rejected_component_count`
- `v2_accepted_nonfloor_trace_fraction`

## 2. Oversegmentation evidence

Oversegmentation is not determined from consolidated count alone. Evidence includes floor-dominated accepted pixels, floor branches, unsupported isolated branches, fragmentation, coverage above floor, and stripe-dominance abstention. No arbitrary branch hard cap.

Full-file (`Am_all_2013-01-01`, 1440 frames): **oversegmentation_suspected = 533**.

Diagnostic set (18 frames): overseg flagged where multi-evidence criteria fire; floor-dominated frames such as 2013 f1440 are not marked geometry-valid with floor branches retained (consolidated 0).

## 3. Synthetic geometry (strict expected behavior)

| Result | Count |
| --- | ---: |
| Pass | **14 / 14** |
| Fail | **0** |

Paired relative comparisons; missing expected measurement fails. Cases cover thin/broadened ridges, parallel/crossing branches, interference/stripe clutter, partial gap, impulses (excluded from accepted), zero/saturated (not assessable).

Evidence: `docs/_phase4b1_synthetic_geometry/synthetic_geometry_report.json`.

## 4. Feature registry completeness

| Metric | Value |
| --- | ---: |
| Registered aggregate feature IDs | **80** |
| Emitted unique IDs (14 synthetic + 18 diagnostics) | **80** |
| emitted − registered | **empty** |

Per-branch geometry stored as `branch_records` (not `v2_branch_N_*` global IDs). Registry: `knowledge_base/FEATURE_REGISTRY_V2.yaml`.

## 5–6. Width geometry and interference overlap

- Local tangent for normal-to-ridge width; separate fixed-V, fixed-H, normal, along-ridge support, true slope-compensated horizontal residual, and normal-width baseline residual.
- Contiguous broadening uses original column coordinates (gaps break runs).
- Floor and interference excluded from width profiles.
- Interference: pre-exclusion plausible mask, interference mask, potential overlap, accepted outside interference, inferred continuation, unresolved occluded fraction — usable fraction not claimed 1.0 by construction.

## 7. Quality gates (full file)

| Category | Count |
| --- | ---: |
| assessable | **703** |
| degraded | **464** |
| interference_limited | **0** |
| not_assessable | **273** |

Floor-clutter burden redesigned so ordinary lower-edge structure does not automatically degrade every nonempty frame. Thresholds are project heuristics (documented in quality module / reports).

## 8. MATLAB / Python parity (truthful)

Cross-runtime = Python executed **and** MATLAB executed **and** results compared.

| Count | Value |
| --- | ---: |
| Total cases | 15 |
| Actual cross-runtime comparisons | **14** |
| Python-only | 1 |
| MATLAB-only | 0 |
| Skipped | 0 |
| Matched valid values | 7 |
| Matched invalid rejections | 7 |
| Failures | 0 |

Invalid probes cover empty/zero/NaN/Inf/wrong dims/mismatched branches/empty or no-stripe interference masks. NaN/Inf rejected as non-finite widths.  
Evidence: `workspaces/_phase4b_parity/parity_report.json`.

## 9. Performance evidence

Archive: `Am_all_2013-01-01.mat` (1440 frames). Compact per-frame JSON only — **not** a complete diagnostic export.

| Metric | Value |
| --- | ---: |
| Frames completed | 1440 |
| Total elapsed (sum of per-frame timings) | **1955.7 s** |
| Median / p95 s/frame | **1.240 / 2.649** |
| Process RSS baseline | **34.1 MB** |
| Process RSS after Amp_all load | **336.0 MB** |
| Process RSS peak (probe) | **354.8 MB** |
| Source matrix | **281.25 MB** |
| Python tracemalloc peak | **~15.4 MB** |
| Cancel-after-30 | completed 30, cancellation true |
| Resume | resumed from 30 → 1440 completed |
| Second-run / cache | cache hits recorded on resume/second pass |
| Failed frame counted as completed | no (cancel stopped at 30; resume continued) |

## 10. Owner-review readiness

| Item | Result |
| --- | --- |
| Diagnostic packages | **18** regenerated under `docs/_phase4b1_diagnostics/` |
| Contact sheets | raw, cand-pre, floor, interference, accepted nonfloor, centerlines, width dir/map |
| Owner geometry review table | **0 completed / 18 pending** — not treated as acceptance |
| Note | Owner review begins only after obvious floor false positives are removed |

## 11. Tests and validators

| Suite / validator | Result |
| --- | --- |
| Phase 4B tests | **25 passed** |
| Full repository suite | **222 passed**, 9 warnings |
| `validate_synthetic_geometry_v2` | OK 14/14 |
| `validate_feature_registry_v2` | OK registry=80 emitted=80 missing=0 |
| `validate_feature_parity` | OK (14 actual cross-runtime) |
| `validate_feature_diagnostics` | OK |
| `validate_feature_shadow_mode` | OK |
| `validate_archive_scan_integrity` | OK |

## Package and EXE

| Artifact | Digest |
| --- | --- |
| EXE | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` SHA-256 **`37c34923cef421e46b05cec00d3f91cee5463512643137f7397d62ef1487386b`** |
| Verification zip | `IML_Phase4B_Verification_Complete.zip` (digest in companion `.sha256`; no source MAT files) |

## Residual risk (not Phase 4C)

Many real frames remain `oversegmentation_suspected` (533/1440 on the full file). Owner visual geometry review is still required. This phase does **not** claim improved morphology accuracy or scientific validation.
