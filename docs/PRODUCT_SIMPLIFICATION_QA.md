# Product Simplification QA — v1.1.1

**Status:** PASS (packaged closure walkthrough completed 2026-08-01)  
**Portable EXE SHA-256:** `DC0239B6CAF120CF1E503E0EE3F80D7D050758B94D8A25676B9B271878A6C317`  
**Manifest:** `dist/IonogramMorphologyLab/BUILD_MANIFEST.json`  
**Evidence log:** `workspaces/_packaged_closure_results.json`  
**Git:** repository initialized; remote `origin` → `https://github.com/PsychicBAM/IonogramMorphologyLab.git`; latest green Actions on `main` (Test + Security checks).  
**Automated tests:** **103 passed** (`python -m pytest`, 2026-08-01 closure).

## Method

1. Rebuilt portable `IonogramMorphologyLab.exe` after Storage clear/restore and RU Storage localization.
2. Verified EXE smoke (`--smoke-test`) and bundled resource parity (i18n, rule pack, USER_GUIDE, icon).
3. Exercised the same build revision with approved MAT `Am_all_2014-09-25.mat` on user-selected drive `D:\IML_Closure_QA`.

## Checklist

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Create project on a user-selected drive | Pass | `D:\IML_Closure_QA\workspace\ClosureQA_*` |
| 2 | Import MAT | Pass | `Am_all_2014-09-25.mat` |
| 3 | Build cache | Pass | FrameStore cache valid, n=1440 |
| 4 | View frame 421 | Pass | shape (256, 400) |
| 5 | Confirm not mixed_spread | Pass | `clean` / R004 |
| 6 | Run selected frame range | Pass | 400–430 step 5 → 7 frames |
| 7 | Confirmation summary matches job | Pass | expected_frames=7 |
| 8 | Inspect supporting / contradicting evidence | Pass | activated R004; disagreement flags recorded |
| 9 | Rules fired / rejected notes | Pass | abstention `dual_axis_thickening_unbalanced_not_mixed` |
| 10 | Frame 800 as frequency-spread candidate only | Pass | `frequency_spread` / R001 / RU «Частотное рассеяние» |
| 11 | Switch RU and EN | Pass | MainWindow language switch |
| 12 | No raw internal tokens on normal RU pages | Pass | including Storage «Обзор…» |
| 13 | Guided / Research / Expert modes | Pass | Guided hides Methods; Expert restores |
| 14 | Desktop shortcut with consent | Pass | `Desktop\Ionogram Morphology Lab.lnk` |
| 15 | Change project/cache/report folders | Pass | settings under `D:\IML_Closure_QA` |
| 16 | Close and reopen; storage paths persist | Pass | SettingsStore reload |
| 17 | Clear cache | Pass | derived.bin removed |
| 18 | No source MAT removed | Pass | sentinel + real MAT preserved |
| 19 | Restore storage defaults | Pass | action completed |
| 20 | Migrate rollback / error message | Pass | warning dialog on unreachable `Z:` target |

## Documentation archive

Superseded landing manuals and historical audits moved under `docs/archive/` (see `DOCUMENTATION_FILE_AUDIT.md`). Canonical public set retained.

## Remaining software limitations

- Interactive human click-through of every menu in a live desktop session was automated via the packaged EXE smoke + build-revision UI harness (offscreen Qt). Visual pixel QA of the EXE window chrome was not separately screenshot-recorded in this pass.
- Results multi-run browser remains limited to the active run.
