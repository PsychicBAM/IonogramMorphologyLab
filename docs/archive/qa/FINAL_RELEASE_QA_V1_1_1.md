# Final Release QA — Ionogram Morphology Lab v1.1.1

| Field | Value |
|-------|-------|
| Product | Ionogram Morphology Lab |
| Version | **1.1.1** |
| QA date | 2026-08-01 (updated after real-MAT viewer crash-fix packaging) |
| Portable EXE SHA-256 | `1fa58a6208e1d57a62b56990c62068e44ad2aa0432aa40e6f6a3736c35737539` |
| Manifest | `dist/IonogramMorphologyLab/BUILD_MANIFEST.json` (gitignored with `dist/`) |

## Verdict

**PASS for GitHub source publication** with external blockers listed. Evidence documents agree: hygiene PASS, usability executed Pass, screenshots are live PNG (schematics SVG separated), Bandit High/Critical 0, pip-audit (requirements file) 0 advisories, MED findings mitigated or accepted with docs. Post-fix packaging confirms the Ionogram Viewer no longer aborts on real-MAT slider interaction.

## Real-MAT viewer crash fix (packaging evidence)

| Item | Result |
|------|--------|
| Root cause | Concurrent `CacheBuildWorker` starts from every slider `valueChanged` while cache was building |
| Fix | Centralized validated frame navigation (`go_to_frame` / `set_current_frame_from_ui`); clamp 1…N; signal blockers; render-on-release + debounce; duplicate cache-build prevention; controlled render-error status |
| Viewer safety tests | **7 passed** (`tests/test_viewer_slider_safety.py`) |
| Full pytest | **77 passed** |
| Real MAT stress | `Am_all_2013-01-01.mat` (1440 frames) — slider spam, first/last, out-of-range clamp, cache-build race — **Pass, no abort** |
| Packaged EXE | Rebuilt after fix; smoke + packaged viewer QA — see checklist |

## Evidence classification

| Area | Classification | Notes |
|------|----------------|-------|
| Unit/regression tests (77) | **Automatically tested** | `pytest` including 7 viewer slider safety tests |
| Hygiene / README / docs / version / v11 release validators | **Automatically tested** | scripts |
| Packaged EXE smoke launch | **Manually/smoke tested** | process alive |
| Real-MAT viewer navigation (post-fix) | **Automatically tested** + packaged smoke | 1440-frame stress; EXE launch |
| Guided workflow + rule + batch + reports + MATLAB teaching run | **Automatically tested** (packaged-evidence session) + UI screenshots **inspected** | `packaged_evidence_session.py` |
| Screenshot readability RU/EN | **Inspected** | PNG from Windows Qt + Segoe UI |
| Russian documentation language | **Inspected** | `RUSSIAN_DOCUMENTATION_LANGUAGE_REVIEW.md` |
| Bandit High/Critical | **Automatically tested** (local venv `.venv-sec`) | exit 0 with `-ll` |
| pip-audit on requirements-base | **Automatically tested** | exit 0; see `DEPENDENCY_AUDIT_V1_1_1.md` |
| Inno Setup installer | **Externally blocked** | ISCC absent |
| Git commit SHA attachment | **Externally blocked** | Git not initialized |
| Human institutional UAT | **Not tested** | owner review recommended |

## Checklist

| Item | Result |
|------|--------|
| Hygiene report contains real run | PASS |
| Usability QA completed (not blank checkboxes) | PASS |
| PNG screenshots replace placeholder-as-screenshot claim | PASS (SVG → `docs/assets/schematics/`) |
| Russian docs reviewed | PASS |
| Bandit/pip-audit status accurate | PASS |
| MED-001/002 mitigated; MED-003 audited | PASS |
| Docs completeness / `validate_docs.py` | PASS |
| Real-MAT viewer slider crash fixed | PASS |
| Portable rebuilt after viewer fix | PASS |
| BUILD_MANIFEST regenerated | PASS |
| Packaged EXE smoke (`--smoke-test` + GUI alive) | PASS |
| Packaged viewer real-MAT QA (1440 frames) | PASS |
| Git readiness commands (except git itself) | PASS |
| No commit / no push performed | PASS |

## Related

- [`CHECKPOINT_IML_V1_1_1_GITHUB_RELEASE_READY.md`](../checkpoints/CHECKPOINT_IML_V1_1_1_GITHUB_RELEASE_READY.md)
- [`USABILITY_QA_EN.md`](USABILITY_QA_EN.md) / [`USABILITY_QA_RU.md`](USABILITY_QA_RU.md)
- [`SECURITY_AUDIT_V1_1_1.md`](../../SECURITY_AUDIT_V1_1_1.md)
- [`REPOSITORY_HYGIENE_REPORT.md`](../../REPOSITORY_HYGIENE_REPORT.md)
- [`DOCUMENTATION_COMPLETENESS_REPORT.md`](../../DOCUMENTATION_COMPLETENESS_REPORT.md)
- [`GIT_READINESS_V1_1_1.md`](GIT_READINESS_V1_1_1.md)
- [`CHANGELOG.md`](../CHANGELOG.md)
