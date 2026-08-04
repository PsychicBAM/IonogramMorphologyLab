"""Compute FORMULA_REGISTRY summary groups from item classifications (Phase 4A.1 / 4A.1b)."""

from __future__ import annotations

from typing import Any

# Map item.classification → summary group key.
CLASSIFICATION_TO_SUMMARY_GROUP: dict[str, str] = {
    "exact_physical_formula": "exact_physical_formulas",
    "exact_signal_processing_formula": "exact_signal_processing_formulas",
    "observational_definition": "observational_definitions",
    "instrument_specific_procedure": "instrument_specific_procedures",
    "morphology_definition": "morphology_definitions",
    "project_engineering_heuristic": "project_engineering_heuristics",
    "unsupported_or_incomplete": "unsupported_or_disabled",
}

SUMMARY_GROUP_KEYS: tuple[str, ...] = (
    "exact_physical_formulas",
    "observational_definitions",
    "exact_signal_processing_formulas",
    "instrument_specific_procedures",
    "morphology_definitions",
    "project_engineering_heuristics",
    "unsupported_or_disabled",
)


def compute_formula_summary(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build summary ID lists from classifications — never hand-maintained duplicates."""
    out: dict[str, list[str]] = {k: [] for k in SUMMARY_GROUP_KEYS}
    for item in items:
        fid = item.get("formula_id")
        if not fid:
            continue
        cls = item.get("classification")
        group = CLASSIFICATION_TO_SUMMARY_GROUP.get(str(cls or ""))
        if group is None:
            out["unsupported_or_disabled"].append(str(fid))
            continue
        out[group].append(str(fid))
    return out


def summary_counts(summary: dict[str, list[str]] | None) -> dict[str, int]:
    summary = summary or {}
    return {k: len(summary.get(k) or []) for k in SUMMARY_GROUP_KEYS}
