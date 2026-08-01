#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.rules.engine import RuleEngine


def main() -> int:
    eng = RuleEngine()
    active = eng.active_rules()
    disabled = [r for r in eng.rules if not r.enabled]
    for r in active:
        if r.threshold_origin == "unsupported":
            print("FAIL unsupported active", r.rule_id)
            return 1
        if not r.source_id and r.threshold_origin == "directly_from_source":
            print("FAIL missing source", r.rule_id)
            return 1
    print(
        f"validate_rule_provenance OK active={len(active)} "
        f"source_traceable={sum(1 for r in active if r.source_id)} disabled={len(disabled)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
