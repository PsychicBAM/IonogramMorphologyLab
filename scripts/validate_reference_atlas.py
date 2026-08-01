#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / "knowledge_base" / "REFERENCE_ATLAS_CASES.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    if len(rows) < 5:
        print("FAIL: too few reference cases")
        return 1
    restricted = 0
    for r in rows:
        if r.get("internal_image_availability") != "available":
            restricted += 1
        if r.get("interpretation_strength") == "mechanism_supported_by_external_measurement":
            # OK if present, but equatorial must warn
            pass
        if "equatorial" in (r.get("station_regime") or "").lower():
            if "kazan" not in (r.get("domain_restrictions") or "").lower() and "no_direct" not in (
                r.get("domain_restrictions") or ""
            ):
                print("FAIL: equatorial case missing domain restriction")
                return 1
    print(f"validate_reference_atlas OK cases={len(rows)} rights_restricted_or_unavailable={restricted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
