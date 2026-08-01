# CHECKPOINT — IML v1.0 Complete Product + MATLAB Studio Ready

**Date:** 2026-08-01  
**Application version:** **1.0.0**  
**Russian product name:** Лаборатория морфологии ионограмм  
**English product name:** Ionogram Morphology Lab  
**Phase:** Complete product release candidate (stop only on genuine external blockers)

| # | Item | Status |
|---|---|---|
| 1 | Application version | **1.0.0** (`src/ionogram_morphology_lab/__init__.py`, `pyproject.toml`) |
| 2 | Portable executable path | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` (~24.7 MB launcher; onedir bundle) |
| 3 | Installer path | Not built — **Inno Setup (ISCC) not installed** (see blockers). Definition: `packaging\IonogramMorphologyLab.iss` → target `installer\IonogramMorphologyLab_Setup_1.0.0.exe` |
| 4 | RU/EN completion | **170** translation keys; parity validated |
| 5 | Language selector location | First-launch dialog + **Settings → General → Interface language / Язык интерфейса** (English / Русский) |
| 6 | Top EN/RU buttons removed | **Confirmed** — toolbar has collapse-nav + language *indicator* only; no `act_lang_*` switchers |
| 7 | Real MAT viewer | Connected via `AppSession` + `FrameStore`; frame/time nav, playback, contact sheets |
| 8 | Cache performance | Zarr `iml2-zarr-frame-v1`, LRU, ±2 prefetch; see IML-2 benchmark docs |
| 9 | Batch workflow | User-facing selection modes + expected-frame preview + pipeline |
| 10 | Automatic analysis | Full pipeline stages selectable (audit → features → rules → reference → optional ML → disagreement → ensemble → abstention → expert) |
| 11 | Feature count | **31** registered features |
| 12 | Rule count | **6** active (+ 1 disabled in pack) |
| 13 | Development models | Model Lab trains sklearn models on user/synthetic labeled sets; **no pre-shipped trained production model** |
| 14 | Calibration status | Not adequate by default — UI explains numerical confidence unavailability |
| 15 | Abstention | Enabled in scientific_strict / analysis settings |
| 16 | MATLAB Studio status | Main-nav section; editor + library + run + results |
| 17 | MATLAB editor features | Tabs, syntax highlight, line numbers, new/open/save, unsaved recovery path, library categories |
| 18 | Detected backends (this host) | `matlab_engine` unavailable; `external_matlab` detected (`D:\MATLAB\R2019a\bin\matlab.EXE`); `octave` not found; `none` always available |
| 19 | MATLAB API function count | **15** helpers under `matlab_helpers\` |
| 20 | Built-in MATLAB examples | **14** teaching examples under `matlab_studio_library\teaching\` |
| 21 | Plugin manifest status | `.iml-matlab.yaml` schema + registry enable/disable |
| 22 | Plugin execution isolation | Separate worker/process runner; failures return structured errors; GUI survives |
| 23 | MATLAB output viewer | Studio results pane: status, stdout/stderr, outputs, provenance |
| 24 | MATLAB versioning and diff | Script library history / SHA / restore |
| 25 | Model Lab status | Import labeled CSV, train, compare, model card (development / research use only) |
| 26 | Results browser | Table + explanation tabs; no bare `null` confidence |
| 27 | Expert review | Dedicated nav + results human-decision actions |
| 28 | Help section count | **58** bilingual sections (includes MATLAB Studio suite) |
| 29 | Settings tab count | **11** (General, Data, Viewer, Performance, Analysis, MATLAB, Models, Reports, Reference Packs, Privacy, Advanced) |
| 30 | Project portability | `projects/portability.py` export/import package (source MAT optional) |
| 31 | Export formats | CSV, JSON, HTML, Markdown (+ reproducibility manifest) |
| 32 | Test count | **39 passed** |
| 33 | Validator results | `validate_v1_all.py` **OK** (full product, MATLAB, plugins, Model Lab, provenance, i18n, packaging, e2e, MVP, forbidden-path optional semantics) |
| 34 | Real-data benchmark | IML-2 real/approved MAT benchmark docs retained; synthetic timings not claimed as final scientific bench |
| 35 | Portable-build test | Exe built; smoke launch started and closed cleanly; `packaging\verify_build.ps1` OK |
| 36 | Installer test | **Blocked externally** — ISCC missing |
| 37 | Source integrity | Source MAT read-only by default; MATLAB runner verifies hashes unchanged unless explicit overwrite path |
| 38 | Known scientific limitations | Provisional KFU metrology; candidate morphology only; no mechanism confirmation from images; development ML not externally validated; Article 3 blinded labels unused |
| 39 | Known software limitations | MATLAB Engine for Python not installed on this host; Octave not installed; Inno Setup not installed; QScintilla optional (PySide6 highlighter used) |
| 40 | Unresolved external requirements | See `IML_V1_REAL_REMAINING_BLOCKERS.md` |

## Product policy changes in v1.0

- Permanent hardcoded Article-path product blocklist **removed**.
- **Protected Scientific Study mode** optional, **off by default**, user-configurable.
- Analysis mode selectable: `fast_preview` | `standard` | `scientific_strict` (recommended default) | `custom`.
- Integrity features retained: SHA, provenance, read-only source MAT, abstention, uncertainty wording.

## Confirmations

- No Article 3 secret/blinded labels used for training or prediction.
- No claim of externally validated ML accuracy.
- Top toolbar EN/RU language buttons removed.
- Portable executable present and smoke-tested.
- All code validators for v1.0 pass.

## Stop (v1.0 baseline)

v1.0 product deliverable complete pending only external packaging/MATLAB-Engine install steps listed in blockers.

---

# EXTENSION — IML v1.1.0 Scientific MATLAB Methods + Rule Builder

**Date:** 2026-08-01  
**Application version:** **1.1.0** (extends v1.0.0; does not replace the shell)

| # | Item | Status |
|---|---|---|
| 41 | Built-in MATLAB method count | **82** under `matlab_builtin\` |
| 42 | Layer-detection method count | **13** (`layer_detection`) + E/Es/F modules |
| 43 | Es method count | **8** (`es_analysis`) |
| 44 | F-layer method count | **10** (`f_layer_analysis`) |
| 45 | Spread-F method count | **9** (`spread_f_analysis`) |
| 46 | Interference method count | **6** (`interference`) |
| 47 | Branch-analysis method count | **6** (`branch_analysis`) |
| 48 | Parameter-estimation method count | **3** MATLAB + Parameters GUI |
| 49 | Active built-in rule packs | **9** versioned packs under `rule_packs\` |
| 50 | Rule Builder status | GUI page **Scientific Rule Builder** — create/version/codegen |
| 51 | Rule Testing Lab status | GUI page — run/sweep/confusion on development rows |
| 52 | `.iml-rulepack` status | Export/import with broken-pack isolation |
| 53 | Source-verification workflow | Statuses draft→…→externally_reviewed; Strict filters approved |
| 54 | Generated MATLAB rule status | `generate_matlab_function` |
| 55 | Generated Python rule status | `generate_python_rule` |
| 56 | Custom-rule versioning | `RuleStore` history under `user_library/rules/_history` |
| 57 | Method-comparison status | GUI page with separate layer/morphology columns |
| 58 | Schematic teaching example count | Documented schematics + generated `.npy` masks |
| 59 | Known unsupported ionogram structures | Es subtype letters mostly disabled pending registry; D-layer not inferred; confirmed O/X from Amp_all alone not claimed |
| 60 | Separate scientific axes | `scientific_outputs` — layer / morphology / ambiguity / quality / parameters |
| 61 | Es subtype registry | `knowledge_base/ES_SUBTYPE_SOURCE_REGISTRY.csv` (no invented active letter list) |
| 62 | Pipeline Builder | GUI with dependency validation |
| 63 | Ionogram Parameters page | Candidate parameters + expert accept/reject |
| 64 | Overlay legend | Color + linestyle + pattern (not color alone) |
| 65 | Help section count (v1.1) | **80** |
| 66 | i18n keys (v1.1) | **175** |
| 67 | Tests (v1.1) | **48 passed** |
| 68 | Validator | `scripts/validate_v11_extension.py` OK |

## v1.1 confirmations

- Built-in MATLAB originals are read-only in Studio; editable copies go to user/project libraries.
- Results never store a single overloaded “ionogram type”.
- Existing v1.0 workflows (viewer, cache, batch, Model Lab, packaging scripts) preserved.
- Synthetic tests are not scientific validation.
