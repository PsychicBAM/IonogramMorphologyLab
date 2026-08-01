# Final Release QA — Ionogram Morphology Lab v1.1.1

| Field | Value |
|-------|-------|
| Product | Ionogram Morphology Lab |
| Version | **1.1.1** |
| QA date | 2026-08-01 |
| Portable EXE SHA-256 | `a6add149d7232ea9dc4d25928ff22c4633f07a407805a6556ee6ea2cb0a47c03` |
| Manifest | `dist/IonogramMorphologyLab/BUILD_MANIFEST.json` (gitignored with `dist/`) |

## Verdict

**PASS for GitHub source publication** with external blockers listed. Evidence documents agree: hygiene PASS, usability 24/24 executed Pass, screenshots are live PNG (schematics SVG separated), Bandit High/Critical 0, pip-audit (requirements file) 0 advisories, MED findings mitigated or accepted with docs.

## Evidence classification

| Area | Classification | Notes |
|------|----------------|-------|
| Unit/regression tests (65) | **Automatically tested** | `pytest` |
| Hygiene / README / docs / version / v11 release validators | **Automatically tested** | scripts |
| Packaged EXE smoke launch | **Manually/smoke tested** | process alive |
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
| Portable rebuilt after fixes | PASS |
| Git readiness commands (except git itself) | PASS |
| No commit / no push performed | PASS |

## Related

- [`CHECKPOINT_IML_V1_1_1_GITHUB_RELEASE_READY.md`](../checkpoints/CHECKPOINT_IML_V1_1_1_GITHUB_RELEASE_READY.md)
- [`USABILITY_QA_EN.md`](USABILITY_QA_EN.md) / [`USABILITY_QA_RU.md`](USABILITY_QA_RU.md)
- [`SECURITY_AUDIT_V1_1_1.md`](SECURITY_AUDIT_V1_1_1.md)
- [`REPOSITORY_HYGIENE_REPORT.md`](REPOSITORY_HYGIENE_REPORT.md)
- [`DOCUMENTATION_COMPLETENESS_REPORT.md`](DOCUMENTATION_COMPLETENESS_REPORT.md)
- [`GIT_READINESS_V1_1_1.md`](GIT_READINESS_V1_1_1.md)
