# Security Audit — v1.1.1

| Field | Value |
|-------|-------|
| **Version audited** | 1.1.1 |
| **Audit date** | 2026-08-01 |
| **Scope** | Application source (`src/ionogram_morphology_lab/`), repository scripts (`scripts/`), CI workflows (`.github/workflows/`), documentation security claims |
| **Out of scope** | Generated `build/` and `dist/` artifacts; end-user workstation hardening; penetration testing; scientific validity |
| **Method** | Manual code review, static pattern grep, dependency audit (`pip-audit` when available), mapping to [Threat model](THREAT_MODEL.md) |

This document is a **release hardening audit**, not a certificate of universal security. Re-run after changes to parsers, archives, reports, subprocess backends, or Model Lab persistence.

---

## Executive summary

| Severity | Count | Notes |
|----------|-------|-------|
| **Critical** | **0** | No default remote attack surface; no unaudited RCE on startup |
| **High** | **0** | No `shell=True`, no `yaml.load(`, no direct `pickle.` in audited source paths |
| **Medium** | 2 mitigated + 1 process | MED-001 joblib trust gates added; MED-002 MATLAB confirmation added; MED-003 requirements audit clean (see DEPENDENCY_AUDIT) |
| **Low** | 4 | Markdown log disclosure, SQLite integrity, incomplete symlink test coverage, settings JSON trust |
| **Info** | 2 | Low-severity Bandit findings under `-ll` threshold; CI Bandit is blocking for High/Critical |

**Release posture:** Acceptable for **1.1.1** GitHub publication. Local Bandit High/Critical = 0; `pip-audit` on `requirements/requirements-base.txt` reported no known vulnerabilities (2026-08-01). Residual risk remains for trusted-path joblib and intentional MATLAB execution.

---

## Controls verified

### YAML safe loading

All audited YAML ingestion uses `yaml.safe_load`:

- `src/ionogram_morphology_lab/rule_builder/packs.py` — pack manifests and rule files
- `src/ionogram_morphology_lab/instrument_profiles/schema.py` — instrument profiles
- `src/ionogram_morphology_lab/matlab_studio/manifest.py` — MATLAB Studio manifests

**CI gate:** `.github/workflows/security.yml` fails if `yaml.load(` appears in `src/` or `scripts/`.

**Assessment:** **Pass** (no unsafe loader in scope).

### Rule pack `import_pack` hardening

`rule_builder/packs.py` implements:

| Control | Limit / behavior |
|---------|------------------|
| Compressed archive size | ≤ 25 MiB |
| Entry count | ≤ 500 |
| Per-entry uncompressed size | ≤ 10 MiB |
| Total uncompressed | ≤ 80 MiB |
| Path rejection | `..`, absolute paths, rooted `\`/`/`, drive letters, UNC |
| Symlinks | Reject Unix symlink external attribute when present |
| Extract location | Temporary directory; install only after validation |

**Test:** `tests/test_v11_scientific_extension.py::test_rule_packs_are_valid_and_broken_archives_are_isolated` — `../escape.txt` rejected, file not written outside temp.

**Assessment:** **Pass** for ZIP slip and zip-bomb limits in this entry point.

### Project package import

`projects/portability.py::_safe_members` resolves each archive member and raises if outside destination root.

**Test:** `tests/test_project_portability.py` — export/import round trip; source MAT excluded by default.

**Assessment:** **Pass** for containment pattern; user must still trust package contents they import.

### HTML report escaping

`reports/export_reports.py::_md_to_simple_html` uses `html.escape` on headings, list items, paragraphs, title, and language code before embedding in HTML template.

**Assessment:** **Pass** for the simple Markdown-to-HTML converter path. CSV/JSON exports are not HTML contexts.

### Subprocess usage

| Location | Pattern | `shell=True` |
|----------|---------|--------------|
| `matlab_studio/runner.py` | `subprocess.run(cmd, ...)` list form | No |
| `matlab_studio/backends.py` | `subprocess.run([...])` | No |
| `scripts/check_repository_hygiene.py` | `git ls-files` via list | No |

**CI gate:** `! rg -n 'shell\s*=\s*True|yaml\.load\(|pickle\.' src scripts`

**Assessment:** **Pass** for shell-flag absence. **Medium residual:** external MATLAB/Octave execution remains intentional, user-triggered code execution.

### Pickle / joblib

Direct `pickle.` **not found** in `src/` or `scripts/`.

`classifiers/model_lab.py` uses `joblib.dump` / `joblib.load` for project-local models.
v1.1.1 adds containment checks: reject `..` / path separators in `model_id`, require `model_card.json`, reject cards marked untrusted, and resolve paths under the project `models/` tree only. Arbitrary file-picker pickle load is not performed.

**Assessment:** **Medium residual** — joblib deserialization remains equivalent to pickle for a *trusted* path that an attacker can already write; mitigated by containment and explicit trust guidance, not eliminated.

---

## Static analysis

| Tool | Command | Result | Classification |
|------|---------|--------|----------------|
| ripgrep unsafe APIs | `rg 'shell\s*=\s*True\|yaml\.load(\|pickle\.' src scripts` | No matches | Info — pass |
| Bandit | `.\.venv-sec\Scripts\python.exe -m bandit -r src -x tests -ll -iii -f txt -o docs/_bandit_local.txt` | **Exit 0** — High/Critical **0** (14 Low reported, not failing `-ll`). CI installs Bandit without `\|\| true` and fails on High/Critical | Pass (High/Critical) |
| pip-audit (local) | `.\.venv-sec\Scripts\python.exe -m pip_audit -r requirements/requirements-base.txt` | **Exit 0** — “No known vulnerabilities found”. Details: [DEPENDENCY_AUDIT_V1_1_1.md](DEPENDENCY_AUDIT_V1_1_1.md) | Pass (requirements file) |
| Repository hygiene | `python scripts/check_repository_hygiene.py` | Secret and absolute-path patterns in tracked docs/src | Low — heuristic |
| README validation | `python scripts/validate_readme.py` | Relative links and version 1.1.1 | Info |
| Version consistency | `python scripts/validate_version_consistency.py` | Active version 1.1.1 | Info |

---

## Dependency audit (`pip-audit`)

When run in a full development environment, `pip-audit` may report **many advisories** across transitive dependencies (e.g. Jinja2, Pillow, urllib3, etc.). Observed characteristics:

- Advisories apply to the **Python environment**, not necessarily reachable code paths in IML.
- The project package is typically **not published to PyPI** under this name; audit tools may note it cannot resolve the local package remotely.
- Remediation is **ongoing** (bump pins, assess reachability), not a single release blocker if no exploitable path is identified in IML workflows.

**Classification:** **Medium (environment)** — track advisories; prioritize parser/image/template libraries used on untrusted input.

---

## Findings register

### MED-001 — joblib model deserialization (mitigated)

| Field | Detail |
|-------|--------|
| Severity | Medium (residual after mitigation) |
| Component | `classifiers/model_lab.py`, `ui/model_lab_page.py` |
| Description | `joblib.load` can execute arbitrary code if model file is attacker-controlled |
| Mitigation in 1.1.1 | Path containment; model card + SHA-256; origin/trust_status; no auto-load on page open; explicit confirmation before first load of imported/unconfirmed models; tests in `tests/test_v111_model_trust.py` |
| Residual | A user who confirms trust for a malicious file still deserializes it |
| User action | Treat models like code; do not confirm foreign models |

### MED-002 — MATLAB Studio subprocess trust boundary (mitigated)

| Field | Detail |
|-------|--------|
| Severity | Medium (residual after mitigation) |
| Component | `ui/matlab_studio_page.py`, `matlab_studio/runner.py` |
| Description | User-initiated MATLAB/Octave run executes `.m` code with user privileges |
| Mitigation in 1.1.1 | Explicit warning: scripts run with OS user permissions; confirmation for imported/non-builtin scripts; display source/SHA/trust/backend/output folder; settings flags for acknowledgment; tests in `tests/test_v111_matlab_trust.py` |
| Residual | Confirmed scripts still run unsandboxed by design |
| User action | Only run trusted scripts; prefer built-in teaching methods |

### MED-003 — Transitive dependency advisories

| Field | Detail |
|-------|--------|
| Severity | Medium (process) |
| Component | Third-party wheels per `pyproject.toml` |
| Description | `pip-audit` may list CVEs with varying relevance |
| Exploitability | Depends on CVE and input path |
| Recommendation | Periodic audit; pin updates in patch releases |
| User action | Maintain updated venv for internet-facing **future** features; local offline use reduces exposure |

### LOW-001 — Report and UI logs expose local paths

Paths selected in file dialogs appear in report log and exported metadata. Expected for reproducibility; risk when sharing artifacts.

### LOW-002 — SQLite integrity not cryptographically signed

Local `project.sqlite` can be edited by any process with file access.

### LOW-003 — Symlink rejection test coverage

Symlink rejection implemented for rule packs; limited automated test on Windows-centric dev environments.

### LOW-004 — Settings JSON import

User can import settings JSON from disk; merged keys should remain reviewed when adding new settings surfaces.

### INFO-001 — Bandit optional locally

CI installs Bandit with `|| true`; developers may skip local Bandit run.

### INFO-002 — pip-audit volume

High advisory count requires human triage, not automated fail-by-default in this release.

### INFO-003 — Screenshot capture stub

`scripts/capture_screenshots.py` documents synthetic capture; does not prove UI security.

---

## Comparison to v1.1.0

| Area | v1.1.0 | v1.1.1 |
|------|--------|--------|
| Rule pack ZIP limits | Partial / evolving | Explicit constants and tests |
| HTML reports | Escaping added/verified | Documented |
| CI security grep | — | `security.yml` |
| Hygiene scanner | — | `check_repository_hygiene.py` |
| Threat model table | Summary | Full per-threat rows |

---

## Recommended follow-up (not blocking 1.1.1)

1. Add Unix CI job step extracting symlink ZIP fixture for `import_pack`.
2. Triage top `pip-audit` findings for h5py/Pillow/Jinja2 reachability from untrusted inputs.
3. Model Lab: optional “foreign model” warning on load when hash not in training manifest.
4. Bandit as required dev extra with documented baseline suppressions if needed.

---

## Sign-off checklist

- [x] Critical findings: **0**
- [x] High findings: **0**
- [x] Medium findings documented with user guidance
- [x] Threat model aligned with code
- [x] Regression tests for ZIP path rejection
- [ ] Configure GitHub private security advisory contact before public launch (maintainer task)

Report new issues per [SECURITY.md](../SECURITY.md).
