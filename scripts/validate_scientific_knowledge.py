#!/usr/bin/env python3
"""Validate scientific knowledge registries."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"
DISABLED = {"candidate_not_ready", "reject", "unverified", "page_missing", "notation_unresolved"}


def main() -> int:
    errors: list[str] = []
    for name in (
        "PROJECT_SCIENTIFIC_SOURCE_INDEX.csv",
        "VERIFIED_FORMULA_REGISTRY.csv",
        "SCIENTIFIC_CLAIM_REGISTRY.csv",
        "TERMINOLOGY_MAPPING.csv",
        "RULE_PACK_IML1.csv",
        "REFERENCE_ATLAS_CASES.csv",
    ):
        p = KB / name
        if not p.exists():
            errors.append(f"missing:{name}")

    # formulas
    with open(KB / "VERIFIED_FORMULA_REGISTRY.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            st = row.get("verification_status", "")
            iml = row.get("iml_status", "")
            if st in DISABLED and iml == "allowed":
                errors.append(f"disabled_formula_allowed:{row.get('formula_id')}")
            if row.get("formula_id") in ("F005", "F006") and iml != "disabled":
                errors.append(f"F005/F006 must be disabled:{row.get('formula_id')}")

    # rules provenance
    with open(KB / "RULE_PACK_IML1.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("enabled", "").lower() == "true":
                if row.get("threshold_origin") == "unsupported":
                    errors.append(f"unsupported_enabled:{row.get('rule_id')}")
                if not row.get("source_id") and row.get("threshold_origin") not in (
                    "engineering_default",
                    "development_calibration",
                    "derived_from_verified_definition",
                    "provisional",
                ):
                    errors.append(f"active_rule_missing_source:{row.get('rule_id')}")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("validate_scientific_knowledge OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
