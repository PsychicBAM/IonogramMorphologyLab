# ML-A.1a.2 — README & Screenshot Refresh Report

**Branch:** `phase/ml-a1-dataset-readiness`
**Date:** 2026-08-06
**Mode:** Docs/images/report only. No product source/test/i18n/packaging changes. **No commit. No push.**

## Release gate (already complete — restated)

| Item | Result |
| --- | --- |
| Owner visual QA | **PASS** |
| Full pytest | **769 passed**, 0 failed (test-only worker API fix; no product rebuild) |
| Validators + hygiene | **All PASS**, hygiene **0** |
| Build Identity | **ML-A.1a.2** |
| Accepted EXE SHA-256 | `67FBB83E6BCECF2A58C719A57AF5E60B9E74FCB31EB1FC130B8BD8DAE6A6A246` |
| Commit / push | **not performed** |

Evidence: [`MLA1_FINAL_RELEASE_GATE_REPORT.md`](MLA1_FINAL_RELEASE_GATE_REPORT.md).

## Discovery

| Item | Finding |
| --- | --- |
| Root READMEs | `README.md`, `README_RU.md` |
| Screenshot convention | `docs/assets/screenshots/<set>/` (historical `v1.1.1/`; new `ml-a1a2/`) |
| Prior README image refs | Pointed at outdated `v1.1.1/*` page tour (missing campaigns / disagreement / ML Data Readiness) |
| Secondary refs retaining `v1.1.1` | `docs/CUSTOM_RULE_BUILDER_EN.md`, `docs/CUSTOM_RULE_BUILDER_RU.md`, archive quick-starts, capture logs |

## README updates

Both `README.md` and `README_RU.md` rewritten with equivalent structure:

- Title / description / scientific status box
- Capabilities
- Module comparison table
- Numbered end-to-end user workflow
- Featured ML-A.1a.2 screenshots (EN/RU twins)
- Quick start / install (verified paths only)
- Projects & MAT
- Expert corpora / campaigns / blind review
- Disagreement analysis
- ML Data Readiness (ML-A.1a.2) + **pilot example clearly labelled as example**
- Integrity / contamination
- Development / verification
- Repo structure
- Runtime / git safety
- Troubleshooting
- Roadmap (**ML-B not started**)
- License / citation (Release **1.1.1** + Build Identity **ML-A.1a.2**)

## Screenshots added

Directory: `docs/assets/screenshots/ml-a1a2/` (1600×900 PNG, synthetic/demo labels).

| Stem | EN | RU |
| --- | --- | --- |
| home | `home_en.png` | `home_ru.png` |
| ionogram_viewer | `ionogram_viewer_en.png` | `ionogram_viewer_ru.png` |
| campaigns | `campaigns_en.png` | `campaigns_ru.png` |
| expert_review | `expert_review_en.png` | `expert_review_ru.png` |
| disagreement_analysis | `disagreement_analysis_en.png` | `disagreement_analysis_ru.png` |
| ml_data_readiness | `ml_data_readiness_en.png` | `ml_data_readiness_ru.png` |
| results | `results_en.png` | `results_ru.png` |

Also: `docs/assets/screenshots/ml-a1a2/CAPTURE_LOG.md`, inventory update in `docs/assets/screenshots/README.md`.

### Capture method note

Captures were taken from the live Qt `MainWindow` in the **ML-A.1a.2 source tree** that matches the accepted packaged build (Build Identity `ML-A.1a.2`; accepted EXE SHA re-verified on disk). Teaching project/corpus labels use sanitized demo names only (`DemoSynthetic`, `demo_*.mat`, `demo_pilot_example`, `Demo pilot readiness (example)`). Ephemeral capture helper lived under gitignored `workspaces/` and is **not** part of the intended commit set.

## Obsolete screenshots removed

**None deleted.** Historical `docs/assets/screenshots/v1.1.1/*.png` remain because secondary docs and archive guides still reference them. Root READMEs no longer use that set as the primary tour.

## Checks

| Check | Result |
| --- | --- |
| `python scripts/validate_docs.py` | **PASS** (after this report exists) |
| `python scripts/check_repository_hygiene.py` | **0 violations** |
| `git diff --check` (touched docs/images) | **clean** (no whitespace errors) |
| Image path links in READMEs | **resolve** |
| EN/RU parity | **equivalent section structure and screenshot twins** |
| Private data in README text | **none** (`E:\`, `C:\Users\`, credentials absent) |
| Private data in screenshots | **none observed** (demo labels only; no owner paths) |
| Full pytest re-run | **not performed** (docs-only supplemental) |

## Git review (no staging)

```
branch: phase/ml-a1-dataset-readiness
```

### Intended for future ML-A.1 release commit — docs/images portion

- `README.md`
- `README_RU.md`
- `docs/MLA1_README_SCREENSHOT_REFRESH_REPORT.md`
- `docs/assets/screenshots/README.md`
- `docs/assets/screenshots/ml-a1a2/CAPTURE_LOG.md`
- `docs/assets/screenshots/ml-a1a2/*.png` (14 files listed above)

**Product / gate inclusion list** (source, tests, validators, MLA1 acceptance docs, etc.) remains in [`MLA1_FINAL_RELEASE_GATE_REPORT.md`](MLA1_FINAL_RELEASE_GATE_REPORT.md) — unchanged by this supplemental task.

### Exclusions (do not stage)

- `config/user_settings.json`
- `workspaces/` (including ephemeral capture helper)
- `review_dataset/`, owner MAT, runtime audits/exports
- `matlab_builtin/` churn, `synthetic_data/*.mat` binary churn
- `matlab_studio_library/`, `model_lab/`, `user_library/`
- `build/`, `dist/`, egg-info, caches
- Historical `v1.1.1` PNGs are **retained** (not deleted); stage only if intentionally refreshing that gallery later

## Verdict

README EN/RU refresh + ML-A.1a.2 featured screenshots are ready to include in the future release commit when the owner authorizes staging. **No commit / no push performed.**
