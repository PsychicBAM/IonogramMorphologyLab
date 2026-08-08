# ML-C.1a Acceptance Report

**Build Identity:** ML-C.1a  
**Protocol (unchanged):** `iml-ml-offline-baselines-0.1.0`  
**Mode:** Offline experimental only  
**Date:** 2026-08-08

## Owner QA findings (ML-C.1 packaged)

NOT PASS — two UX blockers:

1. **Missing / unclear Validate → Run workflow** when a completed experiment was selected. A single contextual primary button swapped to “Export Summary”, so Validate/Run disappeared without a clear next step. Immutability of completed experiments is correct; the UI did not guide “New Experiment / Duplicate” clearly enough.
2. **Incomplete live EN/RU localization** — More menu English under RU; raw lifecycle token `completed` in normal UI; EN body still showing Russian validate-first text after language switch; Frozen Manifest selection could appear blank after switch; absolute artifact path shown in the normal header.

## Fixes

| Area | Change |
|------|--------|
| Primary action bar | Always-visible contextual buttons: New / Validate / Run (disabled until validated) / Export / Cancel |
| Completed UX | Immutable banner; New Experiment + Export Summary; no in-place Run; Verify Integrity (read-only) instead of Revalidate |
| New Experiment | Creates draft, auto-selects it, shows Validate + disabled Run |
| Localization | Full page i18n audit; lifecycle + baseline display labels; More/View menus; worker stages |
| Live switch | Preserves experiment ID, manifest ID, baseline ID, tab, splitters, panel visibility |
| Header | Compact status only; absolute paths only in Technical Details |

## Scientific behavior unchanged

- TRAIN-only fit / DEVELOPMENT-only evaluation  
- Holdout firewall unchanged  
- Feature extractor / baselines / metrics / protocols unchanged  
- ML-D / ML-E not started  

## Verification

- Focused `tests/test_mlc1a_*` + updated `tests/test_mlc1_ui.py`
- Warning audit on `test_mlc1a_*` (no new ML-C.1a product warnings)
- Validators + hygiene 0
- Portable EXE rebuilt  
  SHA-256: `84D3F76200A3BBE7E329CF169DFDE6B1D38EE784133957B51471E71A72BE6530`  
  (differs from ML-C.1 `2CE8C295A79DC601A8F743A53DC879D23641D97F8B4CB2DA4001F516A561DA7D`)
- Packaged-like smoke on `workspaces/MLC1_Offline_Baselines_QA_8a22c20228f2`: PASS
- Full pytest deferred until after owner visual QA
- No commit / no push

## Docs note

While owner QA is pending, ML-C.1 / ML-C.1a should be described as the **current development phase**, not a fully released gate. Screenshot gallery refresh remains deferred.
