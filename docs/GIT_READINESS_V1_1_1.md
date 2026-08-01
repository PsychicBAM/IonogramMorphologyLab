# Git readiness — v1.1.1 (no commit / no push)

**Date:** 2026-08-01  
**Git status:** **Repository not initialized** (`fatal: not a git repository`). No commit SHA exists.

## Commands run

| Command | Result |
|---------|--------|
| `git status --short` | Failed — no `.git` |
| `git ls-files` | Failed — no `.git` |
| `python scripts/check_repository_hygiene.py` | **PASS** (fallback tree scan) |
| `python scripts/validate_readme.py` | **PASS** |
| `python scripts/validate_docs.py` | **PASS** |
| `python scripts/validate_version_consistency.py` | **PASS** |
| `python -m pytest` | **65 passed** |
| `python scripts/validate_v11_release.py` | **PASS** |

## What is ready to track (when owner runs `git init`)

Source and release evidence suitable for a public/private GitHub push:

- `src/`, `tests/`, `scripts/`, `packaging/`, `matlab_builtin/`, `rule_packs/`, `knowledge_base/`, `matlab_helpers/`, `matlab_studio_library/`
- `docs/` including PNG screenshots, schematics, audits, QA reports
- `README.md`, `README_RU.md`, `CHANGELOG.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CITATION.cff`, `.github/`
- `synthetic_data/**/*.mat` (allowed by `.gitignore` exception)
- `config/` defaults (not user-local secrets)
- `.gitignore`, `.gitattributes`, `.editorconfig`, `pyproject.toml`

## Must remain untracked (already gitignored / skipped)

| Path / pattern | Reason |
|----------------|--------|
| `dist/`, `build/` | Portable binaries — release separately if needed (`BUILD_MANIFEST.json` lives under dist) |
| `workspaces/`, `logs/` | User runtime |
| `*.mat` outside `synthetic_data/` | Research archives |
| `*.zarr/` | Derived caches |
| `.venv/`, `.venv-sec/` | Local environments |
| `*.key`, `*.pem`, `.env*` | Secrets |
| `installer/*.exe` | Built installers |
| MATLAB crash dumps | Local crash artifacts |

## Owner next steps (not performed here)

1. `git init` (if desired)  
2. Review `git status` / add remote URL (do not invent URL in docs)  
3. Commit intentionally  
4. Optional: attach portable ZIP + `BUILD_MANIFEST.json` as a GitHub Release asset (keep `dist/` out of the tree)

**This session did not commit and did not push.**
