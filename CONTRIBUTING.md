# Contributing

Thank you for improving Ionogram Morphology Lab. Contributions must preserve reproducibility, scientific traceability, and the distinction between candidate image morphology and physical interpretation.

## Before coding
1. Open an issue describing the problem, scientific motivation, affected workflow and acceptance criteria.
2. Keep changes focused. Do not mix generated artifacts, external data, user workspaces, or unrelated formatting with source changes.
3. For rules or thresholds, record source identifiers, applicability, exclusions, units, limitations and verification status.

## Development workflow
1. Create a Python 3.10+ environment and install `.[dev]`.
2. Run `python -m pytest` and `python scripts/check_repository_hygiene.py` before submitting.
3. Add focused tests for behavior changes; tests must use synthetic or openly distributable fixtures.
4. Update EN and RU documentation together when changing user-visible behavior.

## Pull requests
Explain the problem, solution, validation command, user-facing impact and scientific limitations. Never commit secrets, executable installers, private MAT files, cached Zarr stores, training outputs, or workspaces. Maintainers may request expert review for scientific claims, rule packs, imports, or security-sensitive changes.
