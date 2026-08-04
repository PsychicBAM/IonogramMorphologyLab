# Documentation File Audit — v1.1.1

Inventory and closure status for the product-simplification documentation pass.

## Canonical public set (keep)

| File | Role |
|------|------|
| `README.md` / `README_RU.md` | Entry |
| `docs/USER_GUIDE_EN.md` / `USER_GUIDE_RU.md` | User guides |
| `docs/SCIENTIFIC_GUIDE_EN.md` / `SCIENTIFIC_GUIDE_RU.md` | Scientific guides |
| `docs/DEVELOPER_GUIDE.md` | Developer entry |
| `docs/SECURITY_AND_TRUST.md` | Security/trust landing |
| `CHANGELOG.md` | Release notes |
| `docs/MORPHOLOGY_DECISION_AUDIT_V1_1_1.md` | Current morphology audit |
| `docs/PRODUCT_SIMPLIFICATION_QA.md` | Product QA |
| `docs/SCIENTIFIC_CLASSIFICATION_QA.md` | Classification QA |
| `docs/DOCUMENTATION_FILE_AUDIT.md` | This audit |

Specialized active references (kept): FAQ, Installation, Troubleshooting, Rule Builder/Testing, MATLAB Studio, morphology/parameter methods, architecture, threat model, security audit, schemas/API refs, atlas/feature/rule provenance reports still used as active references.

## Archived in this closure pass (`git mv`)

| From | To |
|------|----|
| `docs/QUICK_START_*.md` | `docs/archive/user-guides/` |
| `docs/COMPLETE_USER_MANUAL_*.md` | `docs/archive/user-guides/` |
| `docs/SCIENTIFIC_METHOD_*.md` | `docs/archive/scientific/` |
| `docs/SCIENTIFIC_LIMITATIONS_*.md` | `docs/archive/scientific/` |
| `docs/DOCUMENTATION_COMPLETENESS_REPORT.md` | `docs/archive/reports/` |
| `docs/RUSSIAN_DOCUMENTATION_LANGUAGE_REVIEW.md` | `docs/archive/reports/` |
| `docs/REPOSITORY_HYGIENE_REPORT.md` | `docs/archive/reports/` |
| `docs/IML0_*` | `docs/archive/historical-audits/` |
| `docs/IML1_MVP_ARCHITECTURE.md` | `docs/archive/historical-audits/` |
| `docs/IML_V1_1_*AUDIT*.md` (historical copies) | `docs/archive/historical-audits/` |

**Note:** `scripts/validate_v11_release.py` regenerates `docs/IML_V1_1_MATLAB_METHOD_IMPLEMENTATION_AUDIT.md` (+ `.json`) as **active** packaging evidence — keep the regenerated root copies; archived copies remain historical snapshots.

Previously archived: checkpoints and older visual/usability QA under `docs/archive/checkpoints/` and `docs/archive/qa/`.

## Intentionally retained (not deleted)

- `LICENSE`, `CITATION.cff`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`
- Active security docs: `SECURITY_AUDIT_V1_1_1.md`, `THREAT_MODEL.md`, `SECURITY_ARCHITECTURE.md`, `DEPENDENCY_AUDIT_V1_1_1.md`
- Active scientific provenance: feature registry, rule provenance, reference atlas reports, MAT import matrix, Article isolation audit
- Specialized guides (MATLAB API, plugin, model lab, layer detection, etc.)
- Current morphology decision audit and QA records

## Status

- Merge into canonical guides: **done** (USER_GUIDE / SCIENTIFIC_GUIDE expanded; archive pointers added).
- Links in README/FAQ/Installation/Troubleshooting/Rule guides: **updated**.
- Validators: re-run after archive (`validate_docs`, `validate_readme`).
