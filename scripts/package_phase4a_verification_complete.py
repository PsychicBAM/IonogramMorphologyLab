#!/usr/bin/env python3
"""Create IML_Phase4A_Verification_Complete.zip (Phase 4A.1 evidence package)."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "IML_Phase4A_Verification_Complete.zip"

INCLUDE = [
    "knowledge_base/SIGNAL_CONTRACTS.yaml",
    "knowledge_base/FORMULA_REGISTRY.yaml",
    "docs/SIGNAL_CONTRACT_GUIDE.md",
    "docs/FORMULA_REGISTRY_GUIDE_EN.md",
    "docs/FORMULA_REGISTRY_GUIDE_RU.md",
    "docs/SCIENTIFIC_SOURCE_TO_CODE_AUDIT.md",
    "docs/PHASE_DATA_INTERPRETATION_AUDIT.md",
    "docs/PYTHON_MATLAB_FORMULA_PARITY.md",
    "docs/ARCHIVE_VARIABLE_AUDIT_4A1.md",
    "docs/PHASE4A1_COMPATIBILITY_NOTE.md",
    "src/ionogram_morphology_lab/scientific_outputs/signal_contracts.py",
    "src/ionogram_morphology_lab/scientific_outputs/formula_registry.py",
    "src/ionogram_morphology_lab/scientific_outputs/formula_summary.py",
    "src/ionogram_morphology_lab/scientific_outputs/quantity.py",
    "src/ionogram_morphology_lab/ui/raw_signals_page.py",
    "src/ionogram_morphology_lab/app/settings_store.py",
    "tests/test_phase4a_signal_formulas.py",
    "tests/test_phase4a1_evidence_corrections.py",
    "tests/test_morphology_classification_correctness.py",
    "scripts/validate_signal_contracts.py",
    "scripts/validate_formula_registry.py",
    "scripts/validate_formula_sources.py",
    "scripts/validate_formula_parity.py",
]


def _add_tree(zf: zipfile.ZipFile, root: Path, arc_prefix: str) -> None:
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and not p.name.startswith("_a3l018"):
            zf.write(p, arc_prefix + "/" + p.relative_to(root).as_posix())


def main() -> int:
    missing = [p for p in INCLUDE if not (ROOT / p).exists()]
    # morphology regression test may use a different name — soft
    soft_missing = [p for p in missing if "morphology_regression" in p]
    hard_missing = [p for p in missing if p not in soft_missing]
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            path = ROOT / rel
            if path.is_file():
                zf.write(path, rel)
        _add_tree(zf, ROOT / "workspaces" / "_phase4a_evidence", "workspaces/_phase4a_evidence")
        _add_tree(zf, ROOT / "workspaces" / "_phase4a_parity", "workspaces/_phase4a_parity")
        # Formula implementations
        for p in (ROOT / "src/ionogram_morphology_lab/scientific_outputs/formulas").glob("*.py"):
            zf.write(p, f"src/ionogram_morphology_lab/scientific_outputs/formulas/{p.name}")
        for p in (ROOT / "matlab_helpers").glob("iml_formula_*.m"):
            zf.write(p, f"matlab_helpers/{p.name}")
    print("Wrote", OUT)
    if hard_missing:
        print("WARN missing:", hard_missing)
    if soft_missing:
        print("WARN optional missing:", soft_missing)
    return 0 if not hard_missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
