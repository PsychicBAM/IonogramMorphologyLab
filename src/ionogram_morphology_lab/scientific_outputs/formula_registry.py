"""Load FORMULA_REGISTRY.yaml and build bilingual explanations (Phase 4A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ionogram_morphology_lab.scientific_outputs.formula_summary import (
    SUMMARY_GROUP_KEYS,
    compute_formula_summary,
)
from ionogram_morphology_lab.utils.paths import app_root

REQUIRED_FIELDS = (
    "formula_id",
    "scientific_concept",
    "classification",
    "exact_source_id",
    "exact_page_or_equation",
    "implementation_status",
    "validation_status",
    "ui_status",
)

CLASSIFICATIONS = {
    "exact_physical_formula",
    "exact_signal_processing_formula",
    "observational_definition",
    "morphology_definition",
    "instrument_specific_procedure",
    "project_engineering_heuristic",
    "unsupported_or_incomplete",
}

EXPRESSION_KINDS = {
    "exact_quotation",
    "translated_quotation",
    "close_paraphrase",
    "project_interpretation",
}

SOURCE_SUPPORTED_CLASSES = {
    "exact_physical_formula",
    "exact_signal_processing_formula",
    "morphology_definition",
}


def registry_path() -> Path:
    return app_root() / "knowledge_base" / "FORMULA_REGISTRY.yaml"


def load_formula_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = list(data.get("items") or [])
    # Always replace hand-copied / "auto" summary with computed groups
    data["summary"] = compute_formula_summary(items)
    data["summary_source"] = "computed_from_classification"
    return data


def list_formulas() -> list[dict[str, Any]]:
    return list(load_formula_registry().get("items") or [])


def formula_summary() -> dict[str, list[str]]:
    return dict(load_formula_registry().get("summary") or {})


def get_formula(formula_id: str) -> dict[str, Any]:
    for item in list_formulas():
        if item.get("formula_id") == formula_id:
            return item
    raise KeyError(formula_id)


def _source_location_precise(loc: Any) -> bool:
    if not isinstance(loc, dict):
        return False
    for key in ("printed_page", "pdf_page", "section", "figure", "table", "equation"):
        val = loc.get(key)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        return True
    return False


def validate_registry_structure(data: dict[str, Any] | None = None) -> list[str]:
    data = data or load_formula_registry()
    errors: list[str] = []
    items = data.get("items") or []
    if not items:
        errors.append("FORMULA_REGISTRY has no items")
    expected_summary = compute_formula_summary(items)
    got_summary = data.get("summary")
    if got_summary != expected_summary:
        errors.append("summary must equal compute_formula_summary(items)")
    for key in SUMMARY_GROUP_KEYS:
        if key not in (got_summary or {}):
            errors.append(f"summary missing group {key}")
    for item in items:
        fid = item.get("formula_id", "<missing>")
        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{fid}: missing {field}")
        cls = item.get("classification")
        if cls not in CLASSIFICATIONS:
            errors.append(f"{fid}: invalid classification {cls!r}")
        ek = item.get("expression_kind")
        if ek is not None and ek not in EXPRESSION_KINDS:
            errors.append(f"{fid}: invalid expression_kind {ek!r}")
        # Numeric / executable formulas that claim a source must have page/equation text
        if cls in {"exact_physical_formula", "exact_signal_processing_formula"}:
            if not item.get("exact_source_id"):
                errors.append(f"{fid}: exact_physical/signal formula requires exact_source_id")
            page = item.get("exact_page_or_equation") or ""
            if not str(page).strip():
                errors.append(f"{fid}: exact formula requires exact_page_or_equation")
        if cls in SOURCE_SUPPORTED_CLASSES and item.get("validation_status") in {
            "source_supported",
            "exact_verified",
        }:
            if not _source_location_precise(item.get("source_location")):
                errors.append(f"{fid}: source-supported item requires structured source_location")
            if not item.get("expression_kind"):
                errors.append(f"{fid}: source-supported item requires expression_kind")
        if item.get("classification") == "project_engineering_heuristic":
            if item.get("ui_status") == "from_source":
                errors.append(f"{fid}: heuristic must not claim ui_status=from_source")
    return errors


def explain_formula(formula_id: str, lang: str = "en") -> str:
    item = get_formula(formula_id)
    ru = lang == "ru"
    status = item.get("ui_status") or item.get("implementation_status")
    status_labels = {
        "from_source": ("из источника", "from a source"),
        "adapted_from_source": ("адаптировано из источника", "adapted from a source"),
        "project_heuristic": ("проектная эвристика", "project heuristic"),
        "not_yet_implemented": ("ещё не реализовано", "not yet implemented"),
        "disabled": ("отключено", "disabled"),
    }
    status_txt = status_labels.get(status, (status, status))[0 if ru else 1]
    expr = item.get("normalized_machine_expression") or item.get("original_expression") or "—"
    vars_ = item.get("variable_definitions") or {}
    var_lines = "\n".join(f"  • {k}: {v}" for k, v in vars_.items()) or ("  —" if not ru else "  —")
    units = item.get("units") or {}
    if ru:
        return (
            f"Что вычисляется: {item.get('scientific_concept')}\n"
            f"Из каких данных: contract={item.get('input_signal_contract') or '—'}\n"
            f"Формула: {expr}\n"
            f"Значение переменных:\n{var_lines}\n"
            f"Единицы: {units}\n"
            f"Источник и страница: {item.get('exact_source_id') or '—'} / {item.get('exact_page_or_equation') or '—'}\n"
            f"Где формула применима: {item.get('domain_of_applicability') or '—'}\n"
            f"Где формула неприменима: {item.get('exclusions') or '—'}\n"
            f"Статус проверки: {item.get('validation_status')} ({status_txt})\n"
            f"Классификация: {item.get('classification')}"
        )
    return (
        f"What is computed: {item.get('scientific_concept')}\n"
        f"From which data: contract={item.get('input_signal_contract') or '—'}\n"
        f"Formula: {expr}\n"
        f"Variable meanings:\n{var_lines}\n"
        f"Units: {units}\n"
        f"Source and page: {item.get('exact_source_id') or '—'} / {item.get('exact_page_or_equation') or '—'}\n"
        f"Where applicable: {item.get('domain_of_applicability') or '—'}\n"
        f"Where not applicable: {item.get('exclusions') or '—'}\n"
        f"Verification status: {item.get('validation_status')} ({status_txt})\n"
        f"Classification: {item.get('classification')}"
    )
