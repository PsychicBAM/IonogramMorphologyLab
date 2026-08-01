#!/usr/bin/env python3
"""Validate the v1.0 product surface without starting the GUI."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def check(ok: bool, message: str, errors: list[str]) -> None:
    if not ok:
        errors.append(message)

def main() -> int:
    errors: list[str] = []
    from ionogram_morphology_lab import __version__
    from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS
    from ionogram_morphology_lab.help.content import HELP_SECTIONS
    en = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    main_window = (ROOT / "src/ionogram_morphology_lab/ui/main_window.py").read_text(encoding="utf-8")
    check(__version__.startswith("1.1"), f"application version is not 1.1.x (got {__version__})", errors)
    check("matlab" in main_window.lower() and "model" in main_window.lower(), "NAV lacks MATLAB/Models", errors)
    forbidden_toolbar = ("choose ru or en using the toolbar", 'qaction("en"', 'qaction("ru"')
    check(not any(token in main_window.lower() for token in forbidden_toolbar), "top EN/RU toolbar actions found", errors)
    check(DEFAULT_SETTINGS["analysis"]["mode"] == "scientific_strict", "analysis.mode default", errors)
    check("matlab" in DEFAULT_SETTINGS, "MATLAB settings missing", errors)
    check(DEFAULT_SETTINGS["privacy"]["protected_study_enabled"] is False, "protected study default", errors)
    check((ROOT / "src/ionogram_morphology_lab/matlab_studio").is_dir(), "matlab_studio missing", errors)
    check((ROOT / "src/ionogram_morphology_lab/classifiers/model_lab.py").is_file(), "model_lab missing", errors)
    check(len(HELP_SECTIONS) >= 50, f"help sections < 50 ({len(HELP_SECTIONS)})", errors)
    check(set(en) == set(ru), "i18n parity", errors)
    if errors:
        print("FAIL", "; ".join(errors)); return 1
    print("validate_full_product OK"); return 0
if __name__ == "__main__":
    sys.exit(main())
