# Dependency Audit — v1.1.1

| Field | Value |
|-------|-------|
| Date | 2026-08-01 |
| Environment | Clean local venv `.venv-sec` (Python 3.14.0) |
| Command | `python -m pip_audit -r requirements/requirements-base.txt -f columns` |
| Exit code | **0** |
| Result | **No known vulnerabilities found** for the requirements file pins |

## Base requirements audited

From `requirements/requirements-base.txt`:

| Dependency | Pin | Advisory | Fixed version | Used by IML? | Input exposure | Decision |
|------------|-----|----------|---------------|--------------|----------------|----------|
| numpy | >=1.24 | none reported | — | Yes (arrays, frames) | MAT-derived arrays | Keep |
| scipy | >=1.11 | none reported | — | Yes (MAT v5/v7, signals) | Untrusted MAT | Keep |
| h5py | >=3.10 | none reported | — | Yes (MAT v7.3) | Untrusted HDF5 | Keep |
| matplotlib | >=3.8 | none reported | — | Yes (rendering) | Derived images | Keep |
| PySide6 | >=6.6 | none reported | — | Yes (GUI) | Local UI | Keep |
| PyYAML | >=6.0 | none reported | — | Yes (profiles, packs) | Untrusted YAML via safe_load | Keep |
| Pillow | >=10.0 | none reported | — | Yes (images/export) | Derived images | Keep |
| scikit-image | >=0.22 | none reported | — | Yes (features) | Derived frames | Keep |
| zarr | >=2.16 | none reported | — | Yes (cache) | Derived cache | Keep |
| numcodecs | >=0.12 | none reported | — | Yes (zarr) | Derived cache | Keep |
| Jinja2 | >=3.1 | none reported | — | Optional/templates | Report text | Keep |
| scikit-learn | >=1.3 | none reported | — | Model Lab | Trusted local datasets | Keep |
| joblib | >=1.3 | none reported | — | Model Lab persistence | Trusted models + trust gate | Keep |

## Notes

1. `pip-audit` against the requirements file in a clean venv reported **zero** known CVEs at audit time.
2. A full-environment audit of a developer site-packages tree may still list transitive advisories unrelated to the pinned requirements file — those are **not** claimed as clean here.
3. CI uploads `pip-audit` artifacts; advisory presence is triaged in this document rather than silently `|| true` on Bandit.
4. Major-version upgrades were **not** applied in this release because the audit found no required fixes and packaging/regression risk is high without a dedicated bump cycle.

## Bandit (companion)

| Command | Result |
|---------|--------|
| `python -m bandit -r src -x tests -ll -iii` | Exit **0** — High/Critical **0**; Low severity issues may exist but do not fail `-ll` |
| Report | `docs/_bandit_local.txt` (local evidence; not a user-facing manual) |
