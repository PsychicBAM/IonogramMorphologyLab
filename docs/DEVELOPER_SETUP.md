# Developer Setup

Use Python 3.10+ in an isolated virtual environment. Install the package with development extras, then run `python -m pytest`. Run `python scripts/check_repository_hygiene.py`, `python scripts/validate_readme.py`, and `python scripts/validate_version_consistency.py` before a pull request.

Keep generated build outputs, workspaces, private MAT data, installers, caches and environment files out of commits. Tests must be deterministic and use synthetic fixtures. MATLAB tests are optional and must be skipped when its engine is unavailable.
