# Phase 4B.2f — Feature Diagnostics Performance, Frame-State Consistency, Responsive Layout

**Status:** implementation complete (runtime / UX only)  
**Date:** 2026-08-03  
**Feature version preserved:** `iml2-0.2.0`  
**Constraints honored:** no V2 geometry/threshold/registry changes; RuleEngine unchanged; V2 shadow-only; Phase 4C not started; no commit/push.

## Stale-frame root cause

Feature Diagnostics loaded frames **synchronously on the UI thread** and applied V2 worker results against the **current spin value** without a request generation token. Rapid navigation (1→2→3→…) could finish older loads after newer selections, so the identity row, raw SHA, and overlays could disagree with the selector (release-blocking scientific identity).

## Worker / state correction

- Immutable `FrameDiagnosticContext` (`ui/frame_diagnostic_context.py`) carries MAT path, source SHA, frame, time, raw SHA, profile, contract, feature version, cache key digest, and `request_generation_id`.
- `FrameLoadWorker` and `V2DiagnosticsWorker` stamp every emission with that generation.
- UI applies results only when `result.request_generation_id == current` and identity fields still match; stale results are discarded silently.
- Obsolete frame loads are cancelled; spinner uses short debounce; Previous/Next remain immediate.
- Job states: idle, loading_frame, checking_cache, loaded_from_cache, computing, rendering, saving_cache, completed, cancelled, failed. Every job ends in exactly one terminal state.
- Cache miss → `recomputed=1`; cache hit → `cache_hits=1`. Cache-write failure does not discard a valid in-session result; UI does not remain stuck in `saving_cache`.

## Real timing breakdown

See `docs/FEATURE_DIAGNOSTICS_PERFORMANCE_AUDIT.md` and `docs/_fd_perf_raw.json`.

Synthetic baseline highlights:

- First frame load ~40 ms; next-frame (cached matrix) ~8 ms  
- Uncached V2 ~0.11 s median; cached deserialize avoids pipeline recompute  
- Overlay recomposite ~1–2 ms with display-layer cache  

## First-run vs cached-run performance

- First V2 run computes and saves the feature cache.  
- Identical rerun loads from V2 cache (`cache_hits=1`) without re-executing Feature Pipeline V2.  
- Profile / feature-version / parameter-hash changes invalidate the key.

## UI-thread work removed

Off the main thread: MAT extract (when not cached in-process), source hashing (with mtime/size reuse), V2 compute, V2 cache serialize/deserialize path inside the worker.  
UI thread: apply display-ready arrays, update widgets, paint.

## Progress throttling

Progress rendering throttled to ~10 Hz (`QTimer` 100 ms) while internal counts remain accurate. Stage updates do not rebuild the feature list or source card.

## Responsive layout changes

- Collapsible Active Source and layer panel  
- Splitter with persisted `general.splitter_states["feature_diagnostics"]`  
- Diagnostic canvas minimum height/width targets for 1366×768  
- Stretch favors the image pane (~55%+ usable width intent)

## Single / Sequence conditional controls

- Single Frame hides sequence-only fields.  
- Sequence shows a selection-type card (frame range / time range / every N / custom) with only relevant fields and natural RU/EN labels (not raw `start`/`end`/`step`/`custom`).

## Layer-render optimization

`DisplayLayerCache` caches Viewer-equivalent / gray / normalized bases and mask layers per context. Checkbox/zoom/opacity/preset changes recomposite only; they never rerun V2 or rewrite the V2 feature cache.

## Sequence lazy rendering

Compact results table first; contact sheet text on explicit request; full diagnostic view when a row is opened.

## Explanation + Phase 4C hand-off (read-only)

Visible RU/EN explanation that Feature Diagnostics does **not** determine final scatter type and does not feed current auto-analysis.  
Read-only panel «Будущий кандидат морфологии» / “Future morphology candidate”: not computed; lists future H/V/coexistence/interference/branch/temporal/uncertainty inputs. No frequency/range/mixed labels generated.

## Tests passed

| Suite | Result |
|-------|--------|
| `tests/test_phase4b2f_performance_and_identity.py` | passed |
| Phase 4B.2c / 4B.2d / 4B.2e UI tests | passed |
| Full repository `pytest tests` | **304 passed** |
| Validators (shadow, registry, synthetic geometry, i18n) | run with EXE packaging |

## Manual QA

Owner packaged-EXE checklist (§16): rapid 1→2→3→90→421 identity match; uncached/cached; layer/zoom; single vs 05:00–07:00 every 10 min; cancel; source switch; dark/light; 1366×768 at 125%/150%. Record responsiveness, timings, stale-result incidents, screenshots.

## Packaged EXE SHA-256

`5AA82DD4204EA8462B383613424FE9941DDE6E2B012C640756C15BBB621BDBEC`

Path: `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe`

## Explicit non-claims

- No scientific validation claimed  
- Feature Pipeline V2 geometry unchanged  
- V2 remains shadow-only  
- Phase 4C classification not enabled  
