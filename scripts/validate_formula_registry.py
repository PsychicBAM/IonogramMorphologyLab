#!/usr/bin/env python3
"""Validate FORMULA_REGISTRY.yaml required fields and classifications."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS  # noqa: E402
from ionogram_morphology_lab.scientific_outputs.formula_registry import (  # noqa: E402
    load_formula_registry,
    validate_registry_structure,
)


def main() -> int:
    data = load_formula_registry()
    errors = validate_registry_structure(data)
    if DEFAULT_SETTINGS.get("analysis", {}).get("scientific_formula_pipeline_enabled", True):
        errors.append("scientific_formula_pipeline_enabled must default to False")
    heuristics = [
        i for i in (data.get("items") or []) if i.get("classification") == "project_engineering_heuristic"
    ]
    for h in heuristics:
        if h.get("ui_status") == "from_source":
            errors.append(f"{h.get('formula_id')}: heuristic marked as from_source")
    if errors:
        print("validate_formula_registry FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("validate_formula_registry OK", len(data.get("items") or []), "items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
