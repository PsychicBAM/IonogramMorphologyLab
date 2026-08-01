# CHECKPOINT — Ionogram Morphology Lab v1.1.1 GitHub Release Ready

**Date:** 2026-08-01  
**Phase:** Final Evidence Closure and Public Release Verification  
**Status:** READY for GitHub source publication (Git not yet initialized)

---

## Evidence classification legend

- **Automatically tested** — machine-executed with pass/fail  
- **Manually tested** — packaged EXE / human-driven steps  
- **Inspected** — content reviewed (screenshots, RU prose)  
- **Externally blocked** — tool/environment unavailable  
- **Not tested** — explicitly out of scope this session  

---

## Checkpoint table

| # | Item | Value / status | Class |
|---|------|----------------|-------|
| 1 | Application version | **1.1.1** | Automatically tested |
| 2 | Portable EXE | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` | Automatically + smoke |
| 3 | EXE SHA-256 | `a6add149d7232ea9dc4d25928ff22c4633f07a407805a6556ee6ea2cb0a47c03` | Automatically tested |
| 4 | BUILD_MANIFEST.json | Present under dist (gitignored) | Automatically tested |
| 5 | Installer (ISCC) | **Not built** — Inno Setup absent; `.iss` retained | Externally blocked |
| 6 | README EN/RU | Polished; PNG heroes; no-code rule sequence | Inspected + validators |
| 7 | Documentation | `validate_docs.py` PASS | Automatically tested |
| 8 | Help sections | 86 + synonyms | Automatically / inspected |
| 9 | Screenshots | **36 PNG** live UI; SVG moved to `docs/assets/schematics/` | Inspected |
| 10 | Rule Builder no-code | Wizard + banner; evidence Pass | Automatically tested |
| 11 | RU language review | `RUSSIAN_DOCUMENTATION_LANGUAGE_REVIEW.md` | Inspected |
| 12 | Tests | **65 passed** | Automatically tested |
| 13 | Hygiene report | Real run PASS @ 2026-08-01 15:12:24 +03 | Automatically tested |
| 14 | Bandit | Local `.venv-sec`: High/Critical **0** (exit 0 `-ll`); CI blocking | Automatically tested |
| 15 | pip-audit | Requirements file: **0** advisories; `DEPENDENCY_AUDIT_V1_1_1.md` | Automatically tested |
| 16 | Critical findings | **0** | Inspected |
| 17 | High findings | **0** | Inspected |
| 18 | Medium findings | MED-001/002 mitigated; MED-003 audited clean | Automatically + inspected |
| 19 | Usability QA | 24/24 executed Pass (EN+RU docs filled) | Automatically + inspected |
| 20 | MATLAB teaching run | External R2019a via `external_matlab` — Pass | Automatically tested |
| 21 | Git commit SHA | **None** — Git not initialized | Externally blocked |
| 22 | Commit / push | **Not performed** (per instructions) | — |
| 23 | Source MAT integrity | Read-only; synthetic only in evidence | Inspected |
| 24 | Scientific limitations | Candidate morphology; no mechanism claims | Inspected |
| 25 | Known technical limits | Optional Engine/Octave; installer blocked; Git absent | Inspected |

---

## Fixes during evidence closure (not v1.2 science)

- Intro panel contrast (dark theme readability)  
- Pipeline Builder checkbox ownership crash  
- Rule Builder Advanced `addTab` bug  
- Screenshot capture uses Windows + Segoe UI (not tofu offscreen glyphs)  
- Model Lab trust/SHA gates; MATLAB run confirmation  
- Hygiene skip `.venv-sec`; security CI without Bandit `|| true`  

---

## Related artifacts

- `docs/FINAL_RELEASE_QA_V1_1_1.md`  
- `docs/USABILITY_QA_EN.md` / `docs/USABILITY_QA_RU.md`  
- `docs/REPOSITORY_HYGIENE_REPORT.md`  
- `docs/SECURITY_AUDIT_V1_1_1.md`  
- `docs/DEPENDENCY_AUDIT_V1_1_1.md`  
- `docs/DOCUMENTATION_COMPLETENESS_REPORT.md`  
- `docs/RUSSIAN_DOCUMENTATION_LANGUAGE_REVIEW.md`  
- `docs/GIT_READINESS_V1_1_1.md`  
- `docs/_packaged_evidence_v111.json`  

**Do not start v1.2.** Owner may initialize Git and publish when ready.
