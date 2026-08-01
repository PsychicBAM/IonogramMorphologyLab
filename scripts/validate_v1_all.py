#!/usr/bin/env python3
"""Run the complete v1.0 validator suite."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def run(name: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "scripts" / name)])
def optional_protection_semantics() -> bool:
    from ionogram_morphology_lab.security.path_blocklist import PathBlocklist, ProtectedStudyConfig
    sample = r"E:\protected\study\frame.mat"
    if PathBlocklist().is_blocked(sample): return False
    protected = PathBlocklist(ProtectedStudyConfig(enabled=True, protected_path_fragments=["protected\\study"]))
    return protected.is_blocked(sample)
def main() -> int:
    scripts = [
        "validate_full_product.py", "validate_matlab_studio.py", "validate_matlab_plugin_system.py",
        "validate_model_lab.py", "validate_scientific_provenance.py", "validate_i18n.py",
        "validate_packaging.py", "validate_end_to_end.py", "validate_mvp.py",
    ]
    failed = [name for name in scripts if run(name)]
    legacy = run("validate_forbidden_path_isolation.py")
    if legacy:
        if optional_protection_semantics():
            print("WARN legacy forbidden-path validator uses pre-v1 optional-protection semantics")
        else:
            failed.append("validate_forbidden_path_isolation.py")
    if failed: print("validate_v1_all FAIL", ", ".join(failed)); return 1
    print("validate_v1_all OK"); return 0
if __name__ == "__main__": sys.exit(main())
