# Changelog

This project follows [Semantic Versioning](https://semver.org/). Software version is separate from scientific validation status — see [Scientific Guide](docs/SCIENTIFIC_GUIDE_EN.md).

## [1.1.1] - 2026-08-01

Release hardening for GitHub publication: usability, bilingual documentation, repository hygiene, and security controls for untrusted imports.

### Product simplification closure (same 1.1.1)

- Morphology false-`mixed_spread` root cause fixed (local ridge thickness + dual-axis gates); real frame **421** → `clean`; frame **800** → frequency-spread candidate.
- UI: collapsible nav, menus/toolbar, guided batch confirmation, results evidence panel, Storage settings (migrate / clear cache / restore defaults), branded icon, opt-in desktop shortcut.
- Documentation consolidated to canonical guides; superseded manuals/checkpoints archived under `docs/archive/`.
- Automated suite and packaged-EXE closure walkthrough recorded in `docs/PRODUCT_SIMPLIFICATION_QA.md` and `docs/SCIENTIFIC_CLASSIFICATION_QA.md`.
- Repository is a GitHub project with green Actions on `main` (see latest successful Test / Security checks runs).

### Added

- **Home workflow dashboard** with recommended step path, status colours, and **Continue recommended step** navigation.
- **UX interface modes:** Guided, Research, and Expert (Settings persist per installation).
- **Rule Builder no-code wizard** with bilingual intro panels, condition preview, and versioned rule storage.
- **Help synonyms** and expanded in-app help entries for Home, MATLAB Studio, and Rule Builder topics.
- Bilingual quick-start, manual, troubleshooting, FAQ, morphology/parameter guides, and rule-testing documentation.
- Repository validators: `scripts/check_repository_hygiene.py`, `scripts/validate_readme.py`, `scripts/validate_version_consistency.py`.
- GitHub templates (issues, pull request), `security.yml` and `test.yml` CI workflows.
- Security documentation: [Threat model](docs/THREAT_MODEL.md), [Security audit v1.1.1](docs/SECURITY_AUDIT_V1_1_1.md), [Security architecture](docs/SECURITY_ARCHITECTURE.md).
- Usability and documentation completeness report templates under `docs/`.
- Teaching screenshot placeholders under `docs/assets/screenshots/` (synthetic data only).

### Changed

- Product-facing metadata, About dialog, settings defaults, and packaging identify **1.1.1** as the active release.
- Rule pack `import_pack` enforces entry count, compressed/uncompressed size limits, path safety (`..`, absolute, drive/UNC), and symlink rejection on Unix external attributes.
- HTML report export applies `html.escape` to user-influenced text in the simple Markdown-to-HTML path.
- YAML configuration and rule packs load via `yaml.safe_load` throughout audited import paths.
- README and README_RU rewritten with reciprocal EN/RU links, honest scientific limitations, and repository-relative links only.

### Security

- Static CI grep blocks `shell=True`, `yaml.load(`, and direct `pickle.` in `src/` and `scripts/`.
- Project package import uses resolved-path containment (`_safe_members`) against ZIP slip.
- Repository hygiene scanner rejects likely secrets and absolute local paths in `docs/` and `src/`.

### Reliability

- Broken rule-pack archives fail closed without writing outside the temporary extract directory (regression test).
- Portable project packages exclude source MAT by default; import supports explicit source path relinking.
- Version consistency script rejects obsolete active product versions in key metadata files.
- **Ionogram Viewer:** fixed real-MAT process abort when moving the frame/time slider after import. Root cause was concurrent cache builds started from every slider `valueChanged` tick. Navigation now uses a single validated path (`go_to_frame` / `set_current_frame_from_ui`) with clamped 1-based indices, `QSignalBlocker` sync, render-on-release plus debounce, duplicate cache-build rejection, and controlled render-error status (no silent broad swallow). Regression: `tests/test_viewer_slider_safety.py` (7 tests). Later product-simplification closure suite: see current pytest count in QA docs (not the historical 77-test checkpoint).

### Documentation

- Fixed mojibake and thin stubs in landing README files and security docs.
- Expanded Quick Start and Custom Rule Builder guides (EN/RU).

### Known limitations (unchanged scope)

- Model Lab remains **development / research use only** — not validated production ML.
- MATLAB Studio execution remains user-controlled and optional.
- Supported MAT layouts are those audited in your session — not all vendor variants are tested.

## [1.1.0] - 2026-07-01

### Added

- Rule Builder, Rule Testing Lab, method comparison, pipeline builder, and development Model Lab workflows.
- Source/provenance-aware analysis, MATLAB Studio integration, and bilingual reporting.

## [1.0.0] - 2026-05-01

### Added

- Initial desktop workflow for MAT import, frame viewing, morphology proposals, expert review, and export.

[1.1.1]: https://github.com/ORG/REPOSITORY/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ORG/REPOSITORY/compare/v1.0.0...v1.1.1
[1.0.0]: https://github.com/ORG/REPOSITORY/releases/tag/v1.0.0
