# Developer Guide — Ionogram Morphology Lab 1.1.1

## Setup and run

```powershell
cd IonogramMorphologyLab
python -m pip install -e ".[dev]"
./scripts/run_dev.ps1
./scripts/run_tests.ps1
```

Package: `src/ionogram_morphology_lab`. Entry: `ionogram_morphology_lab.app.main:main`.

## Required checks

```powershell
python -m pytest
python scripts/check_repository_hygiene.py
python scripts/validate_readme.py
python scripts/validate_docs.py
python scripts/validate_version_consistency.py
python scripts/validate_v11_release.py
```

Portable rebuild: `packaging/build_portable.ps1`, then `python scripts/write_build_manifest.py`.  
Current packaged closure evidence: [PRODUCT_SIMPLIFICATION_QA.md](PRODUCT_SIMPLIFICATION_QA.md) (EXE SHA-256 recorded there).

## Documentation policy

- Keep public entry points in the root READMEs, User Guides, Scientific Guides, this guide, Security and Trust, and the changelog.
- Put dated checkpoints and superseded QA evidence under `docs/archive/`; do not treat archived records as current instructions.
- Keep API, schema, rule-pack, data-format, and MATLAB references where they are active and useful.
- Update EN/RU user-facing documentation together.

## Safety and scientific boundaries

Do not access Article 3 forbidden paths or train on Article 3 labels. Treat imports, user rules, MATLAB scripts, model artifacts, and project packages as untrusted input. A passing test suite or synthetic example does not establish scientific validity.

See [Architecture](ARCHITECTURE.md), [Testing](TESTING.md), [Security and Trust](SECURITY_AND_TRUST.md), and [Scientific Classification QA](SCIENTIFIC_CLASSIFICATION_QA.md).
