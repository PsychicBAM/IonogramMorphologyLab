# CHECKPOINT — IML-1 Standalone Bilingual MVP Ready

**Date:** 2026-08-01  
**Phase:** IML-0 + IML-1 complete (stop here)

| # | Item | Status |
|---|---|---|
| 1 | Application root | repository root (`IonogramMorphologyLab/`) |
| 2 | Application version | `0.1.0` |
| 3 | Desktop framework | **PySide6 / Qt** (no blocker) |
| 4 | RU/EN status | Bilingual UI + reports; first-launch language dialog; in-app switch |
| 5 | Translation-key count | **65** keys; EN/RU parity validated |
| 6 | MAT versions supported | v5/v7 (SciPy), v7.3 HDF5 (h5py) |
| 7 | Import adapters | `scipy_mat_v5`, `hdf5_mat_v73`, `known_kfu_cyclone`, `generic_user_profile`, `optional_matlab_engine` |
| 8 | Instrument-profile count | **2** YAML (`kfu_cyclone_2013_2014`, `generic_user_template`) + wizard-saved user profiles |
| 9 | KFU profile verification status | **provisional** (Gate2 calibration open; author-attested coords) |
| 10 | Generic profile wizard status | Implemented (14-step state machine) |
| 11 | Large-file cache status | Zarr chunked derived cache with provenance JSON |
| 12 | Ionogram-rendering status | Raw PNG render + 5×5 contact sheet |
| 13 | Raw/derived view separation | Raw default; derived labeled `DERIVED_DIAGNOSTIC` / `view_kind` |
| 14 | Data-quality audit status | File + frame audit statuses implemented |
| 15 | Feature count | **31** registered features |
| 16 | Similarity-method count | **14** methods |
| 17 | Reference-source count | Core literature IDs in source index (A3L006/007/014/015/018 + project protocols) |
| 18 | Reference-case count | **9** metadata cases (REF001–REF009) |
| 19 | Rights-restricted reference count | **9** unavailable in default install (metadata only) |
| 20 | Active rule count | **6** (R001–R006) |
| 21 | Source-traceable rule count | **6** |
| 22 | Provisional / development-calibrated rules | R001/R002/R004 use `development_calibration`; R003/R006 derived; R005 engineering_default |
| 23 | Disabled unsupported rule count | **1** (R099) |
| 24 | Disagreement types | **13** flags in `DISAGREEMENT_TYPES` |
| 25 | Abstention status | Supported (`abstain`, O/X path, out_of_domain, quality) |
| 26 | Batch-processing status | Pause/resume/cancel controller; per-file error isolation |
| 27 | Export formats | CSV, JSON, HTML, Markdown, bibliography, reproducibility manifest, SQLite project |
| 28 | SQLite project status | Implemented (`projects`, `runs`, `frame_results`, `audit_log`) |
| 29 | Audit-trail status | Append-only audit_log; human decisions separate from auto_json |
| 30 | Article 3 forbidden-path status | Blocklist active; validator OK |
| 31 | Article 3 secret-access status | **None** — refused / not used |
| 32 | Article 3 decision-access status | **None** — not read |
| 33 | Solar/dawn/dusk feature leakage status | **None** in morphology feature registry / engine |
| 34 | Source-file integrity | Batch test verifies SHA-256 unchanged |
| 35 | Network/telemetry status | Disabled by design; no telemetry libraries |
| 36 | Tests | **17 passed** (`pytest`) |
| 37 | Validators | `validate_mvp.py` OK (architecture, knowledge, atlas, rules, isolation, i18n) |
| 38 | Visual QA | Documented in `docs/IML1_VISUAL_QA_*.md`; nearest/no-smoothing checks in tests |
| 39 | Portable build status | Scripts prepared (`packaging/build_portable.ps1`); exe not built in this checkpoint run |
| 40 | Installer status | Inno Setup definition prepared; builds if ISCC present, else documented blocker |
| 41 | Known scientific limitations | No absolute calibration; nominal virtual height; O/X not separable; development thresholds; metadata-only atlas images |
| 42 | Known software blockers | Optional MATLAB Engine not required; Inno Setup may be absent; full-day Amp_all RAM heavy without cache |
| 43 | Final ML model trained? | **No** |
| 44 | Article 3 predictions produced? | **No** |
| 45 | Manuscript modified? | **No** |

## Confirmations

- No Article 3 data unlocked.
- No training on Article 3 labels.
- No comparison with Article 3 human decisions.
- No dawn/dusk statistics performed.
- No claim of independent validation.
- No physical-mechanism confirmation from morphology alone.

## Stop

IML-0 + IML-1 delivery complete. Further phases require explicit new instructions.
