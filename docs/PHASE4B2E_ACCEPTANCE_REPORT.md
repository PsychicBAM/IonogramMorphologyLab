# Phase 4B.2e — Canonical Display Orientation, Frame/Time Selection, Sequence Diagnostics, Responsive V2 Execution

**Status:** implementation complete (display / UX / cache / async only)  
**Date:** 2026-08-03  
**Feature version preserved:** `iml2-0.2.0`  
**Constraints honored:** Phase 4B.3 scientific geometry unchanged; Feature Registry V2 unchanged; production RuleEngine unchanged; morphology classifications unchanged; V2 shadow-only; Phase 4C not started; no commit/push.

## Display-orientation root cause

Ionogram Viewer renders the scientific amplitude matrix with matplotlib `imshow(..., origin="lower")`, so scientific row 0 (lowest nominal virtual height / floor band) appears at the **bottom** of the plot.

Feature Diagnostics previously painted `QImage` / PNG buffers with scientific row 0 at the **top** (top-left raster convention). That produced a vertical inversion relative to Viewer: floor at the top, traces reversed — even when raw-array SHA values matched.

**Conclusion:** equal scientific-matrix SHA does not imply equal display orientation. Display and science must be separated.

## Canonical transform implementation

Module: `src/ionogram_morphology_lab/rendering/display_transform.py`  
Transform version: `iml-display-v1`

| Concept | Behavior |
|---------|----------|
| Scientific matrix orientation | Unchanged numeric arrays from `extract_frame_consistent`; never flipped for UI repair |
| Display orientation | `apply_display_transform` → vertical flip for top-left raster (QImage / PNG / FD overlays) |
| Exported-image orientation | Same display transform as on-screen FD layers |
| Viewer matplotlib path | Scientific matrix + `matplotlib_imshow_origin()` → `"lower"` (parity with flipud + top-left) |

Orientation identity object (`DisplayOrientationIdentity`):

- `matrix_origin` = `row0_low_nominal_height`
- `display_origin` = `image_top_left`
- `row_zero_display_location` = `bottom`
- `vertical_flip_applied` = `true`
- `horizontal_flip_applied` = `false`
- `transform_version` = `iml-display-v1`

Consumers of the same transform:

- Ionogram Viewer (`ionogram_render.py`)
- Feature Diagnostics raw / gray / jet bases (`fd_display.py`)
- masks, centerlines, branch labels, H/V direction overlays
- exported diagnostic PNGs and orientation JSON

## Viewer / Diagnostics orientation evidence

Automated (`tests/test_phase4b2e_display_and_diagnostics.py`):

- asymmetric corner-marker fixture (distinct TL/TR/BL/BR scientific values)
- display top-left = scientific high-row marker after flipud
- masks share the exact transform as raw
- RC mapping places scientific `(0,0)` at display bottom
- transpose and horizontal-only equality fail the parity checks
- Viewer render meta records `display_orientation` and `scientific_matrix_mutated: false`

Manual packaged-EXE checklist (§14 A) remains required on real `Am_all_*.mat` frames for floor / frequency / height direction confirmation at owner displays.

## Source-action labels

| Action | RU | EN | Semantics |
|--------|----|----|-----------|
| Activate | Активировать для анализа | Activate for Analysis | Compatible inventory MAT → active for Viewer / Batch / Feature Diagnostics; no reimport |
| Deactivate | Отключить от анализа | Deactivate for Analysis | Clears active session source; inventory + physical file kept; reactivatable |
| Remove | Убрать из проекта | Remove from Project | Inventory entry only; never deletes physical MAT |

Deactivate tooltip (RU): «Файл останется в проекте и на компьютере. Его можно снова активировать для анализа.»  
EN equivalent on the same control.

Applied in Active Source card, Import file rows, confirmations, empty/inactive states, Help (`help/content.py` import + Feature Diagnostics topics), and `docs/USER_GUIDE_RU.md` control table.

Lifecycle: **Activate for Analysis ↔ Deactivate for Analysis** (separate from Remove from Project).

## Frame / time selection controls

Feature Diagnostics section **«Выбор кадра» / “Frame Selection”**:

- frame number, interpreted time, First / Previous / Next / Last
- −N / +N minutes, jump interval, exact-time selector
- use current Viewer frame; send current frame to Viewer; auto-sync with Viewer
- status: frame X of N, mapped time, provisional-time warning, source filename, raw-frame SHA

Frame change: loads new raw immediately, clears previous overlays, tries V2 cache, otherwise shows that V2 has not been run for the frame. Stale masks are not kept.

## Single-frame mode

RU **«Один кадр»** / EN **Single Frame** — detailed inspection of one frame with Viewer sync, overlays, human summary, and feature details.

## Sequence mode

RU **«Последовательность»** / EN **Sequence** — explicit range / step / custom list / every-N minutes. Pre-run summary shows MAT, start/end, interval, frame count, profile, feature version, output folder estimate, cache status. Does not silently analyse all 1440 frames when a short selection is chosen.

## Sequence result presentation

After sequence analysis: table of frames (time, quality, trace found, branch count, interference, oversegmentation, H/V validity, cached/new/failed). Contact-sheet style list; selecting a row opens that frame’s single-frame diagnostic view. Filters for failed / uncertain / oversegmentation / no valid trace; export selected diagnostics.

## V2 cache key and behavior

Module: `cache/v2_feature_cache.py` under `{settings.cache_dir()}/v2_features/`.  
**Distinct from Viewer FrameStore render cache.**

Key components:

- source MAT SHA-256
- frame index
- profile ID
- signal-contract ID
- feature version (`iml2-0.2.0`)
- algorithm-parameter hash
- canonical extractor version (`extract_frame_consistent_v1`)

Any mismatch → cache miss / not used.  
Clear V2 cache for current source never deletes or modifies the MAT.

Cache status labels (RU / EN): Не рассчитано / Not computed; Рассчитывается / Computing; Загружено из кэша / Loaded from cache; Рассчитано заново / Recomputed; Кэш устарел / Cache stale; Ошибка / Error.

Actions: Recalculate this frame; Recalculate selected sequence; Clear V2 cache for current source; Open cache details.

## First-run versus cached-run timing

Async worker (`ui/v2_diagnostics_worker.py` on `QThread`) stages: loading numeric frame → quality → representations → trace → interference → consolidation → widths → diagnostics → saving cache.

Expandable **«Почему выполняется расчёт» / “Why the calculation runs”** explains Viewer cache vs V2 computation, first-run cost, and invalidation on profile / feature version / parameters. After completion, stage timings (load / extract / widths / diagnostics / serialization / total) are shown when available.

Evidence: `test_async_worker_single_frame` — first run `recomputed == 1`; identical second run `cache_hits == 1`.

## Cancellation / responsiveness

V2 runs off the Qt UI thread. Single-frame and sequence runs expose progress, cancel, cache hit/miss counts, and (for sequences) frame X of N and percent. Progress updates are monotonic in the worker. Pause/resume is supported where the job architecture allows safe interruption; cancel always clears the running flag.

## Modal-to-inline mismatch behavior

| Situation | UX |
|-----------|----|
| Expected frame change / Viewer sync | Silent clear of stale overlays + non-blocking inline note |
| Expected source switch | Clear overlays + inline note; load new raw / cache if present |
| Unexpected integrity conflict (same path, known SHA vs on-disk hash change) | Blocking modal |

Ordinary navigation must not spam «Несовпадение кадра Viewer и диагностики…» modals.

## Owner geometry-review workflow

In-UI steps:

1. Choose active Am_all source (Activate for Analysis).
2. Choose one frame or a sequence.
3. Confirm Viewer-equivalent orientation.
4. Run V2 or load cached result.
5. Toggle layers / view presets.
6. Read the human summary.
7. Inspect H/V directions.
8. Mark geometry review: acceptable / unacceptable / uncertain + comment.

Review records link source SHA, frame, feature version, and diagnostics cache ID under the project `feature_diagnostics/geometry_reviews/` tree. This is **geometry review only**, not morphology ground truth.

## View presets / diagnostic image

Presets: Исходная ионограмма; След и осевая линия; Помехи; Ширины; Все диагностические слои.  
Base view switch: Viewer-equivalent color / raw grayscale diagnostic / normalized diagnostic. Display color does not change numeric analysis. Default after V2 keeps Viewer-equivalent source under selected overlays.

## Tests passed

| Suite | Result |
|-------|--------|
| `tests/test_phase4b2e_display_and_diagnostics.py` | passed |
| `tests/test_phase4b2c_active_source.py` + `tests/test_phase4b2d_active_source_ux.py` | passed |
| Full repository `pytest tests` | **286 passed** |
| `validate_feature_shadow_mode.py` | OK |
| `validate_feature_registry_v2.py` | OK registry=93 |
| `validate_synthetic_geometry_v2.py` | OK 17/17 `iml2-0.2.0` |
| `validate_i18n.py` | OK |
| `validate_docs.py` | OK |

Covered: RU/EN activate/deactivate wording; deactivate keeps inventory + file; reactivate without reimport; display orientation / corner markers / no flip or transpose mismatch; masks follow raw transform; frame and exact-time selection; frame change clears overlays with inline note; cache restore / stale version rejection; single + sequence selection; cache clear preserves MAT; async cache hit; RuleEngine untouched; V2 shadow-only; `FEATURE_VERSION == iml2-0.2.0`.

## Manual QA

Packaged-EXE checklist (owner):

**A. Orientation** — same frame in Viewer and Feature Diagnostics; floor, trace, frequency, height; toggle every mask.  
**B. Frame selection** — frames 1, 90, 421, 1301, 1440; exact time; prev/next; ±30 minutes.  
**C. Sequence** — 05:00–07:00 every 10 minutes; short custom list; cancel; contact sheet; open one result.  
**D. Cache** — first run; repeat hit; profile/version invalidation.  
**E. Source lifecycle** — Deactivate / Activate; MAT A → B; overlays cleared.

Capture RU/EN screenshots at 1366×768 and 1920×1080 at 100% / 125% / 150%.

Automated suite covers functional behavior; visual confirmation on real Am_all archives remains an owner step.

## Packaged EXE SHA-256

`17D176E8E146D7457357777B403BFBA25F3D37288D46DD653807009831F56EB0`

Path: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Explicit non-claims

- No scientific validation claimed
- No morphology accuracy improvement claimed
- Feature Pipeline V2 measurements, thresholds, consolidation, branch isolation, and H/V width calculations unchanged
- V2 remains shadow-only / not production default
- Phase 4C not started
