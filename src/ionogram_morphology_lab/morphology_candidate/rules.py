"""Load versioned provisional morphology-candidate ruleset."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_candidate.types import deterministic_hash
from ionogram_morphology_lab.utils.paths import app_root

_DEFAULT_RULESET = app_root() / "config" / "morphology_candidate_rules_v0_1.json"


def ruleset_path() -> Path:
    return Path(_DEFAULT_RULESET)


@lru_cache(maxsize=4)
def load_ruleset(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else Path(_DEFAULT_RULESET)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data.get("provisional", False):
        raise ValueError("ruleset must be provisional=true for Phase 4C.1")
    if data.get("scientifically_validated", True):
        raise ValueError("ruleset must have scientifically_validated=false")
    if data.get("production_enabled", True):
        raise ValueError("ruleset must have production_enabled=false")
    return data


def ruleset_hash(ruleset: dict[str, Any] | None = None) -> str:
    rs = ruleset if ruleset is not None else load_ruleset()
    return deterministic_hash(rs)


def threshold(ruleset: dict[str, Any], name: str) -> Any:
    entry = ruleset["thresholds"][name]
    return entry["value"]
