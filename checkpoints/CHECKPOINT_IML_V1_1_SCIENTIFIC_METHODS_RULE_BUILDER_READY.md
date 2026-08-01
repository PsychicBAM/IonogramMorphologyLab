# CHECKPOINT — IML v1.1 Scientific Methods + Rule Builder Ready

**Date:** 2026-08-01  
**Application version:** **1.1.0**  
**Baseline:** extends completed v1.0.0 without replacing the application shell  
**Russian product name:** Лаборатория морфологии ионограмм  
**English product name:** Ionogram Morphology Lab

This is the **canonical v1.1 release checkpoint**. Do not treat the v1.0 checkpoint extension appendix as the sole v1.1 record.

| # | Item | Status |
|---|---|---|
| 1 | Application version | **1.1.0** |
| 2 | Portable executable | `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` (rebuilt in hardening) |
| 3 | Installer | ISS targets `IonogramMorphologyLab_Setup_1.1.0.exe` (ISCC may be absent) |
| 4 | Built-in MATLAB `.m` count | **82** |
| 5 | MATLAB implementation audit | `docs/IML_V1_1_MATLAB_METHOD_IMPLEMENTATION_AUDIT.md` |
| 6 | Fully implemented scientific methods | **72** fully_implemented; placeholders **0** |
| 7 | Teaching / wrapper / disabled classes | wrapper 5; teaching 4; disabled 1 |
| 8 | Layer / Es / F / Spread-F / interference / branch / parameter modules | Present under `matlab_builtin\` |
| 9 | Built-in rule packs | **9** (non-empty) — `docs/IML_V1_1_RULE_PACK_AUDIT.md` |
| 10 | Rule Builder | End-to-end create/version/codegen/test/export/import/disable |
| 11 | Rule Testing Lab | Run, threshold sweep, confusion (development rows) |
| 12 | `.iml-rulepack` | Export/import with broken-pack isolation |
| 13 | Separate scientific axes | layer / morphology / ambiguity / quality / parameters |
| 14 | Overloaded ionogram type | **Absent** (validator rejects) |
| 15 | Ionogram Parameters page | Explicit implementation states; no unexplained empties |
| 16 | Method Comparison | Separate columns |
| 17 | Pipeline Builder | Dependency validation |
| 18 | Es subtype registry | `knowledge_base/ES_SUBTYPE_SOURCE_REGISTRY.csv` |
| 19 | Help sections | **80** |
| 20 | i18n keys | **186** (parity enforced) |
| 21 | About dialog | Shows version **1.1.0** |
| 22 | Real MATLAB `-batch` smoke | **11/11 ok** on `Am_all_2013-01-01.mat` via R2019a (`workspaces/_v11_matlab_smoke/smoke_report.json`) |
| 23 | Source MAT integrity in smoke | Unchanged SHA |
| 24 | Tests | **48 passed** |
| 25 | Validators | `validate_v11_extension.py` OK; `validate_v11_release.py` OK; `validate_v1_all.py` OK |
| 26 | Release notes | `docs/RELEASE_NOTES_1.1.0_EN.md` / `_RU.md` |
| 27 | Rule pack audit | `docs/IML_V1_1_RULE_PACK_AUDIT.md` (9 non-empty packs) |
| 28 | Parameters page audit | `docs/IML_V1_1_PARAMETERS_PAGE_AUDIT.md` |
| 29 | Portable contents | 82 `.m` methods + 9 packs + Es registry + i18n + help in `_internal` |
| 30 | Packaged exe smoke | Launch/close clean |

## Confirmations

- No placeholder MATLAB method counted as a completed scientific method.
- Built-in methods remain read-only; editable copies go to user/project libraries.
- Synthetic tests are not scientific validation.
- External blockers only: MATLAB Engine for Python (optional), Inno Setup (optional), Octave (optional).

## Stop

v1.1 portable release hardening complete. Do not begin v1.2 features from this checkpoint.
