#!/usr/bin/env python3
"""Create IML_Phase4B_Verification_Complete.zip (no source MAT files)."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "IML_Phase4B_Verification_Complete.zip"

INCLUDE_GLOBS = [
    "src/ionogram_morphology_lab/features/v2/**/*.py",
    "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py",
    "src/ionogram_morphology_lab/app/settings_store.py",
    "knowledge_base/FEATURE_REGISTRY_V2.yaml",
    "matlab_helpers/iml_v2_*.m",
    "scripts/validate_feature_*.py",
    "scripts/validate_archive_scan_integrity.py",
    "scripts/validate_formula_parity.py",
    "scripts/validate_synthetic_geometry_v2.py",
    "scripts/export_feature_diagnostics_v2.py",
    "scripts/run_feature_pipeline_v2_*.py",
    "scripts/regenerate_feature_registry_v2.py",
    "scripts/audit_archive_variables_4a1.py",
    "scripts/package_phase4b_verification.py",
    "tests/test_phase4b_feature_pipeline_v2.py",
    "docs/FEATURE_PIPELINE_V2_*.md",
    "docs/PYTHON_MATLAB_FORMULA_PARITY.md",
    "docs/_phase4b1_diagnostics/**/*",
    "docs/_phase4b1_synthetic_geometry/**/*",
    "docs/_phase4b1_fullfile_perf/*.md",
    "docs/_phase4b1_fullfile_perf/*.json",
    "docs/_phase4b1_fullfile_perf/per_frame/*.json",
    "docs/_phase4b3_iml2-0.2.0_diagnostics/**/*",
    "docs/_phase4b3_iml2-0.2.0_synthetic_geometry/**/*",
    "docs/_phase4b3_iml2-0.2.0_fullfile_perf/*.json",
    "docs/_phase4b3_iml2-0.2.0_fullfile_perf/per_frame/*.json",
    "workspaces/_phase4a_evidence/archive_variable_audit.json",
    "workspaces/_phase4a_evidence/archive_scan_meta.json",
    "workspaces/_phase4a_parity/**/*",
    "workspaces/_phase4b_parity/**/*",
    "docs/PHASE4B_ACCEPTANCE_REPORT.md",
    "docs/PHASE4B2_ACCEPTANCE_REPORT.md",
    "docs/PHASE4B3_ACCEPTANCE_REPORT.md",
    "scripts/run_feature_pipeline_v2_perf_orchestrator.py",
]


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for pattern in INCLUDE_GLOBS:
        files.extend(ROOT.glob(pattern))
    # de-dupe; exclude MAT
    out = []
    seen = set()
    for p in files:
        if not p.is_file():
            continue
        if p.suffix.lower() == ".mat":
            continue
        if p.stat().st_size > 50 * 1024 * 1024:
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return sorted(out)


def main() -> int:
    files = _iter_files()
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=str(p.relative_to(ROOT)).replace("\\", "/"))
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    (ROOT / "IML_Phase4B_Verification_Complete.sha256").write_text(
        f"{digest}  IML_Phase4B_Verification_Complete.zip\n", encoding="utf-8"
    )
    print("Wrote", OUT, "files=", len(files), "sha256=", digest[:16] + "…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
