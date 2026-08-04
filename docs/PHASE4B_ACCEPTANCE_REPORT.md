# Phase 4B.1 Acceptance Report

**Phase:** 4B.1 — Real-Frame Geometry Correction and Evidence Completion  
**Feature version:** `iml2-0.1.0`  
**Flag:** `scientific_feature_pipeline_v2_enabled` default **false** (unchanged)  
**Classification accuracy:** not claimed  
**Phase 4C:** not started  

## 0. Phase 4A evidence pre-flight

| Check | Result |
| --- | --- |
| Archive scan JSON hash integrity | OK — hash stored only in `archive_scan_meta.json`; validator `validate_archive_scan_integrity.py` |
| Formula parity counts | `total_cases=25`; `cross_runtime_cases=24`; `python_only_cases=1` (`vh_nonnumeric`); summary matches calculated counts |

## 1. Centerline consolidation (blocker)

| Metric | Result |
| --- | --- |
| Raw component counts (examples) | 2013-01-01 f421: **51**; f720: **76**; 2014-09-25 f421: **54**; f720: **62**; 2014-10-15 f720: **58** |
| Consolidated branch counts (same) | f421: **6**; f720: **12**; f421: **13**; f720: **10**; f720: **10** |
| Frames still oversegmentation-suspected (18-frame diagnostic set) | **12 / 18** |
| Policy | No hard cap; open-ended counts + `plausibility_warning_above=16`; branch O/X / multi-reflection / overlapping-layer / branch persistence abstain when overseg suspected |

## 2–4. Registry and width coordinates

| Item | Result |
| --- | --- |
| Registry feature count | **63** |
| `v2_centerline_count` | Open-ended + `plausibility_warning_above` (no silent clip) |
| Separate width metrics | `fixed_vertical_axis`, `fixed_horizontal_axis`, `slope_compensated_horizontal_residual`, `normal_to_ridge`, `along_ridge_support_length` |
| Input signal contract | `kfu_amp_all_v1` (registry default + per-feature) |

## 5–7. Real diagnostics and owner review

| Item | Result |
| --- | --- |
| Diagnostic frames exported | **18** under `docs/_phase4b1_diagnostics/` (includes 2014-10-15 evening 1201–1431) |
| Required package files | Present (masks, overlays, `identity.json`, `features.json`, `component_decisions.json`) |
| Owner geometry review | **0 completed / 18 pending** — table not marked owner-reviewed |
| Guide wording (EN/RU) | “Synthetic geometry tests + automatic real-frame shadow audit; owner review pending.” |

## 8. MATLAB / Python V2 parity

| Item | Result |
| --- | --- |
| Status | `ok` (optional mode; MATLAB path resolved including R2019a candidates) |
| Helpers compared | vertical width, horizontal width, branch separation, interference stripe burden |
| Counts | total 15; cross-runtime 14; python-only 1; fail 0 |
| Evidence | `workspaces/_phase4b_parity/parity_report.json` (+ stdout/stderr) |

## 9. Validators

| Validator | Result |
| --- | --- |
| Registry | OK (63 features) |
| Diagnostics | OK |
| Shadow mode | OK (RuleEngine unchanged; flag default false) |
| Synthetic geometry | **14/14 PASS** |

## 10. Full-file performance (1440 frames)

| Metric | Value |
| --- | --- |
| Archive | `Am_all_2013-01-01.mat` |
| Frames completed | **1440** |
| Total elapsed | **1934.1 s** (~32.2 min) |
| Median / p95 per frame | **1.450 / 2.238 s** |
| Peak traced memory | **15.6 MB** |
| Source SHA unchanged | yes |
| Resume / cancel hooks | resume supported; cancellation flag recorded |
| Note | Not extrapolated from 15 frames |

## 11. Package

`IML_Phase4B_Verification_Complete.zip` — see companion `.sha256` (no source MAT files).

## 12. Production safety

| Item | Result |
| --- | --- |
| Production RuleEngine | Unchanged |
| Morphology Results | Unchanged by V2 shadow path |
| Feature Pipeline V2 default | **false** |
| EXE SHA-256 | `C1DCB22A34349BC726E5EC09CA2C9217DD5834264EA200E2B826FC4EFE9A8D9D` |

## Residual geometry risk

Several real frames still mark **oversegmentation_suspected** after consolidation (e.g. raw 76 → consolidated 12). Branch-dependent interpretations abstain on those frames. **Do not begin Phase 4C until owner visual geometry review accepts the diagnostics.**
