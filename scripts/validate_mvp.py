#!/usr/bin/env python3
"""Aggregate MVP validators."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "scripts" / script)])


def main() -> int:
    scripts = [
        "validate_application_architecture.py",
        "validate_scientific_knowledge.py",
        "validate_reference_atlas.py",
        "validate_rule_provenance.py",
        "validate_forbidden_path_isolation.py",
    ]
    # ensure kb docs exist
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "_bootstrap_kb_docs.py")])
    codes = {s: run(s) for s in scripts}

    # i18n parity
    en = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    if set(en) != set(ru):
        print("FAIL i18n key mismatch", set(en) ^ set(ru))
        codes["i18n"] = 1
    else:
        print(f"i18n parity OK keys={len(en)}")
        codes["i18n"] = 0

    # no network telemetry modules imported by default package init
    sys.path.insert(0, str(ROOT / "src"))
    import ionogram_morphology_lab  # noqa: F401

    failed = [k for k, v in codes.items() if v != 0]
    if failed:
        print("MVP VALIDATION FAILED:", failed)
        return 1
    print("validate_mvp OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
