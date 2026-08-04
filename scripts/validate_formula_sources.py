#!/usr/bin/env python3
"""Ensure source-supported formulas/definitions cite precise locations (Phase 4A.1)."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.scientific_outputs.formula_registry import (  # noqa: E402
    EXPRESSION_KINDS,
    list_formulas,
)

VAGUE_PATTERNS = [
    re.compile(r"operational\s+classes?", re.I),
    re.compile(r"operational\s+morphology", re.I),
    re.compile(r"source\s+discussion", re.I),
    re.compile(r"book\s+chapter", re.I),
    re.compile(r"pages?\s+unknown", re.I),
    re.compile(r"pp?\.\s*\d+\s*[–-]\s*\d+\s*;?\s*operational", re.I),
]

SOURCE_REQUIRED_CLASSES = {
    "exact_physical_formula",
    "exact_signal_processing_formula",
    "morphology_definition",
}

ALLOWLIST_SOURCE_IDS = {"A2_PROTOCOL", "CALSTAT", "GETION", "FREG", "CLM"}


def _location_precise(loc: object) -> list[str]:
    """Return which precise keys are present."""
    if not isinstance(loc, dict):
        return []
    hits = []
    for key in ("printed_page", "pdf_page", "section", "figure", "table", "equation"):
        val = loc.get(key)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        hits.append(key)
    return hits


def main() -> int:
    sources: dict[str, dict] = {}
    idx = ROOT / "knowledge_base" / "PROJECT_SCIENTIFIC_SOURCE_INDEX.csv"
    with idx.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sources[row["source_id"]] = row
    errors: list[str] = []
    for item in list_formulas():
        fid = item.get("formula_id")
        cls = item.get("classification")
        sid = item.get("exact_source_id")
        page = (item.get("exact_page_or_equation") or "").strip()
        loc = item.get("source_location")
        ek = item.get("expression_kind")

        if cls in SOURCE_REQUIRED_CLASSES:
            if not sid:
                errors.append(f"{fid}: missing exact_source_id")
            elif sid not in sources and sid not in ALLOWLIST_SOURCE_IDS:
                errors.append(f"{fid}: unknown source_id {sid}")
            if not page:
                errors.append(f"{fid}: missing exact_page_or_equation")
            for pat in VAGUE_PATTERNS:
                if page and pat.search(page):
                    errors.append(f"{fid}: vague exact_page_or_equation rejected: {page!r}")
                    break
            precise = _location_precise(loc)
            if not precise:
                errors.append(
                    f"{fid}: source-supported class requires structured source_location "
                    f"with at least one of printed_page/pdf_page/section/figure/table/equation"
                )
            if not ek:
                errors.append(f"{fid}: missing expression_kind")
            elif ek not in EXPRESSION_KINDS:
                errors.append(f"{fid}: invalid expression_kind {ek!r}")
            # Do not claim source verification from a broad page range alone
            if isinstance(loc, dict):
                pp = loc.get("printed_page")
                if isinstance(pp, str) and re.search(r"\d+\s*[–-]\s*\d+", pp):
                    errors.append(f"{fid}: printed_page must be a single page, not a range")

        if cls == "project_engineering_heuristic" and item.get("ui_status") == "from_source":
            errors.append(f"{fid}: heuristic presented as literature equation")

        # morphology with project_interpretation must not claim exact_verified
        if ek == "project_interpretation" and item.get("validation_status") == "exact_verified":
            errors.append(f"{fid}: project_interpretation must not claim exact_verified")

    if errors:
        print("validate_formula_sources FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("validate_formula_sources OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
