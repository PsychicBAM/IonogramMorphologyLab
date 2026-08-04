#!/usr/bin/env python3
"""Create IML_Phase4A1b_Verification.zip — corrected/new evidence only."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "IML_Phase4A1b_Verification.zip"

FILES = [
    "knowledge_base/FORMULA_REGISTRY.yaml",
    "knowledge_base/SIGNAL_CONTRACTS.yaml",
    "src/ionogram_morphology_lab/scientific_outputs/formula_summary.py",
    "src/ionogram_morphology_lab/scientific_outputs/formula_registry.py",
    "src/ionogram_morphology_lab/scientific_outputs/signal_contracts.py",
    "src/ionogram_morphology_lab/scientific_outputs/formulas/axes.py",
    "src/ionogram_morphology_lab/scientific_outputs/formulas/trace_metrics.py",
    "src/ionogram_morphology_lab/importers/adapters.py",
    "src/ionogram_morphology_lab/cache/frame_store.py",
    "src/ionogram_morphology_lab/matlab_studio/api_bridge.py",
    "src/ionogram_morphology_lab/ui/raw_signals_page.py",
    "src/ionogram_morphology_lab/projects/pipeline.py",
    "matlab_helpers/iml_formula_bin_to_mhz.m",
    "matlab_helpers/iml_formula_bin_to_nominal_height_km.m",
    "matlab_helpers/iml_formula_local_width_bins.m",
    "scripts/validate_formula_parity.py",
    "scripts/validate_formula_sources.py",
    "scripts/validate_formula_registry.py",
    "scripts/validate_signal_contracts.py",
    "scripts/audit_archive_variables_4a1.py",
    "scripts/export_phase4a_evidence_bundle.py",
    "tests/test_phase4a1_evidence_corrections.py",
    "tests/test_phase4a1b_foundation.py",
    "tests/test_morphology_classification_correctness.py",
    "docs/FORMULA_REGISTRY_GUIDE_EN.md",
    "docs/FORMULA_REGISTRY_GUIDE_RU.md",
    "docs/SCIENTIFIC_SOURCE_TO_CODE_AUDIT.md",
    "docs/SIGNAL_CONTRACT_GUIDE.md",
    "docs/ARCHIVE_VARIABLE_AUDIT_4A1.md",
    "docs/PHASE4A1_COMPATIBILITY_NOTE.md",
    "docs/PYTHON_MATLAB_FORMULA_PARITY.md",
]


def _add_tree(zf: zipfile.ZipFile, root: Path, arc_prefix: str) -> None:
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and not p.name.startswith("_a3l018"):
            zf.write(p, f"{arc_prefix}/{p.relative_to(root).as_posix()}")


def main() -> int:
    missing = [p for p in FILES if not (ROOT / p).is_file()]
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in FILES:
            path = ROOT / rel
            if path.is_file():
                zf.write(path, rel)
        _add_tree(zf, ROOT / "workspaces" / "_phase4a_evidence", "workspaces/_phase4a_evidence")
        _add_tree(zf, ROOT / "workspaces" / "_phase4a_parity", "workspaces/_phase4a_parity")
    print("Wrote", OUT)
    if missing:
        print("WARN missing:", missing)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
