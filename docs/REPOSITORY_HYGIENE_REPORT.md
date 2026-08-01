# Repository Hygiene Report — v1.1.1

**Report status:** COMPLETED (real local runs)  
**Script:** [`scripts/check_repository_hygiene.py`](../scripts/check_repository_hygiene.py)  
**Product version:** 1.1.1

---

## Latest run metadata

| Field | Value |
|-------|-------|
| Local date/time | **2026-08-01 15:12:24 +03:00** |
| Prior evidence run | 2026-08-01 14:50:22 +03:00 |
| Git repository | **Not initialized** — no commits; SHA unavailable (not invented) |
| Branch | N/A |
| Runner | local Windows host |
| Python version | **Python 3.14.0** |
| Scan mode | Fallback full-tree scan (skipping `.venv`, `.venv-sec`, `build`, `dist`, `workspaces`, `logs`, caches) |
| Command | `python scripts/check_repository_hygiene.py` |

Companion commands (same session):

| Command | Result |
|---------|--------|
| `python scripts/validate_readme.py` | **PASS** |
| `python scripts/validate_version_consistency.py` | **PASS** |
| `python scripts/validate_docs.py` | **PASS** |
| `python scripts/validate_v11_release.py` | **PASS** |
| `python -m pytest` | **65 passed** |

---

## Summary

| Field | Value |
|-------|-------|
| Result | **PASS** |
| Violation count | **0** |
| Release gate | **Closed (PASS)** |

### Per-rule status

| Rule ID | Check | Status | Count |
|---------|-------|--------|-------|
| HYG-001 | Large file (>50 MiB) | PASS | 0 |
| HYG-002 | MAT outside `synthetic_data/` | PASS | 0 |
| HYG-003 | Possible secret patterns | PASS | 0 |
| HYG-004 | Absolute local paths in `docs/` / `src/` | PASS | 0 |
| HYG-005 | `.zarr` | PASS | 0 |
| HYG-006 | Key material (`*.pem` / `*.key`) | PASS | 0 |
| HYG-007 | MATLAB crash dumps | PASS | 0 |
| HYG-008 | Workspace SQLite | PASS | 0 |

### Command output summary

```text
Repository hygiene summary:
  large_file: 0
  mat_outside_synthetic: 0
  possible_secret: 0
  absolute_local_path: 0
  tracked_zarr: 0
  tracked_key_material: 0
  matlab_crash_dump: 0
  workspace_db: 0
  total_violations: 0
Repository hygiene passed.
```

**Note:** An earlier failed run scanned `.venv-sec` site-packages (false positives on `cacert.pem` / auth modules). The hygiene skip list now excludes `.venv-sec`; that environment is gitignored and is not release content.

---

## Release gate checkboxes

- [x] Hygiene executed and passed (real output above)
- [x] README / version / docs validators executed and passed
- [x] No invented commit SHA
- [x] Template “pending” fields removed
