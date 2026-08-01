#!/usr/bin/env python3
"""Validate package architecture presence."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = [
    "src/ionogram_morphology_lab/app/main.py",
    "src/ionogram_morphology_lab/ui/main_window.py",
    "src/ionogram_morphology_lab/importers/adapters.py",
    "src/ionogram_morphology_lab/instrument_profiles/wizard.py",
    "src/ionogram_morphology_lab/rendering/ionogram_render.py",
    "src/ionogram_morphology_lab/features/extract.py",
    "src/ionogram_morphology_lab/similarity/compare.py",
    "src/ionogram_morphology_lab/rules/engine.py",
    "src/ionogram_morphology_lab/disagreement/engine.py",
    "src/ionogram_morphology_lab/reference_atlas/atlas.py",
    "src/ionogram_morphology_lab/projects/pipeline.py",
    "src/ionogram_morphology_lab/security/path_blocklist.py",
    "src/ionogram_morphology_lab/i18n/en.json",
    "src/ionogram_morphology_lab/i18n/ru.json",
    "config/instrument_profiles/kfu_cyclone_2013_2014.yaml",
    "pyproject.toml",
]


def main() -> int:
    missing = [r for r in REQ if not (ROOT / r).exists()]
    if missing:
        print("FAIL missing:")
        for m in missing:
            print(" -", m)
        return 1
    print("validate_application_architecture OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
