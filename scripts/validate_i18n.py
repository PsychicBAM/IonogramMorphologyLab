#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    base = ROOT / "src/ionogram_morphology_lab/i18n"
    en, ru = (json.loads((base / f"{x}.json").read_text(encoding="utf-8")) for x in ("en", "ru"))
    required = {"nav.matlab", "settings.interface_language"}
    errors = []
    if set(en) != set(ru): errors.append("EN/RU key parity")
    if not required <= set(en): errors.append("required keys")
    source = (ROOT / "src/ionogram_morphology_lab/ui/main_window.py").read_text(encoding="utf-8").lower()
    if "choose ru or en using the toolbar" in source: errors.append("top language button requirement")
    if errors: print("FAIL", "; ".join(errors)); return 1
    print("validate_i18n OK"); return 0
if __name__ == "__main__": sys.exit(main())
