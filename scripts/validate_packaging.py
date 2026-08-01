#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    required = [
        ROOT / "packaging/build_portable.ps1",
        ROOT / "packaging/build_installer.ps1",
        ROOT / "packaging/verify_build.ps1",
        ROOT / "packaging/IonogramMorphologyLab.iss",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    exe = ROOT / "dist/IonogramMorphologyLab/IonogramMorphologyLab.exe"
    if missing: print("FAIL missing", ", ".join(missing)); return 1
    if exe.exists() and exe.stat().st_size == 0: print("FAIL empty portable executable"); return 1
    if not exe.exists(): print("WARN portable executable not built; scripts present")
    print("validate_packaging OK"); return 0
if __name__ == "__main__": sys.exit(main())
