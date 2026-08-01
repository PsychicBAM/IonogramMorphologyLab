# CHECKPOINT — IML-2 Real Viewer, Help, Settings, Performance Ready

**Date:** 2026-08-01  
**Application version:** 0.2.0  
**Phase:** IML-2 complete (stop here)

| # | Item | Status |
|---|---|---|
| 1 | Real imported viewer | Connected via `AppSession` + `FrameStore`; opens after import |
| 2 | Synthetic demo separation | Separate nav: Synthetic teaching demo / Учебная синтетическая демонстрация |
| 3 | Frame-index control | Spin box + slider (1-based archive IDs) |
| 4 | Time control | HH:MM edit; provisional KFU mapping minute=index−1 |
| 5 | Navigation controls | First/prev/next/last + jump ±N minutes |
| 6 | Playback | Play/pause/loop; speeds 0.5–10 fps; Space shortcut |
| 7 | Contact-sheet support | 5×5 from real frames with pre-summary |
| 8 | Batch-selection modes | single, frame_range, time_range, full_day, custom_list, contact_sheet |
| 9 | Default interval | **10 minutes** (`DEFAULT_KFU_INTERVAL_MINUTES`) |
| 10 | Expected-frame preview | Human explanation (e.g. step 121 → 12 frames) |
| 11 | Cache format | Zarr `iml2-zarr-frame-v1`, chunks 256×400 |
| 12 | Cache provenance | identity key = SHA + variable + profile + format + layout |
| 13 | First-cache-build timing | ~0.52 s on synthetic demo (see benchmark docs) |
| 14 | Cached-frame timing | LRU hit ~0 s on synthetic; chunk read after clear ~0.005 s |
| 15 | Prefetch status | Default ±2 neighbors |
| 16 | LRU status | Configurable (`performance.lru_capacity`, default 16) |
| 17 | GUI responsiveness | Cache build on `QThread`; progress bar |
| 18 | Settings-section count | **8** tabs (General/Data/Viewer/Performance/Analysis/Reports/Privacy/Advanced) |
| 19 | Help-section count | **28** |
| 20 | Contextual tooltip count | **13** `tip.*` keys (+ ? buttons in Viewer) |
| 21 | Onboarding status | Optional first-run wizard; “Do not show again” |
| 22 | Results-browser status | Table + 8 tabs; JSON only in Technical |
| 23 | Null-confidence explanation | Presenter text RU/EN (no bare `null` in overview) |
| 24 | Scientific-basis presentation | Readable formula/claim cards |
| 25 | Atlas presentation | Cards + rights-unavailable rights text |
| 26 | Import/audit presentation | Human cards + expandable technical JSON |
| 27 | Profile presentation | Structured card + advanced raw toggle |
| 28 | RU/EN parity | **153** keys; validator OK |
| 29 | Active-language synchronization | Toolbar ↔ Settings language combo |
| 30 | Source-file integrity | SHA unchanged in cache/batch tests |
| 31 | Article 3 isolation | Blocklist preserved; validator OK |
| 32 | Strict scientific mode | Forced enabled in SettingsStore |
| 33 | Tests | **26 passed** |
| 34 | Validators | `validate_mvp.py` OK |
| 35 | Visual QA | `docs/IML2_VISUAL_QA_*.md` |
| 36 | Performance benchmark | `docs/IML2_PERFORMANCE_BENCHMARK_*.md` + raw JSON |
| 37 | Known limitations | Full-day KFU bench needs user `--mat`; Matplotlib render still costly; provisional time not metrology |
| 38 | ML model trained? | **No** |
| 39 | Article 3 prediction produced? | **No** |
| 40 | Manuscript modified? | **No** |

## Confirmations

- No Article 3 secrets/labels/dawn-dusk analysis.
- No silent scientific threshold changes.
- Provenance, abstention, uncertainty, blocklist, read-only MAT preserved.

## Stop

IML-2 delivery complete. Further phases require explicit new instructions.
