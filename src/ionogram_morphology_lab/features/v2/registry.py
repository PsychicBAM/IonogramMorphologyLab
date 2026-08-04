"""Load FEATURE_REGISTRY_V2.yaml and explain measured features."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION


def registry_path() -> Path:
    here = Path(__file__).resolve()
    candidates = []
    for parent in here.parents:
        candidates.append(parent / "knowledge_base" / "FEATURE_REGISTRY_V2.yaml")
    candidates.append(Path.cwd() / "knowledge_base" / "FEATURE_REGISTRY_V2.yaml")
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


@lru_cache(maxsize=4)
def _load_feature_registry_v2_cached(path_str: str) -> dict[str, Any]:
    with open(path_str, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_feature_registry_v2(path: Path | None = None) -> dict[str, Any]:
    p = path or registry_path()
    return _load_feature_registry_v2_cached(str(p.resolve()))


def _feature_id(entry: dict[str, Any]) -> str | None:
    return entry.get("feature_id") or entry.get("id")


def list_feature_ids(registry: dict[str, Any] | None = None) -> list[str]:
    reg = registry or load_feature_registry_v2()
    feats = reg.get("features") or reg.get("feature_registry") or []
    if isinstance(feats, dict):
        return list(feats.keys())
    out = []
    for f in feats:
        if isinstance(f, dict):
            fid = _feature_id(f)
            if fid:
                out.append(fid)
    return out


def feature_entry(feature_id: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    reg = registry or load_feature_registry_v2()
    feats = reg.get("features") or reg.get("feature_registry") or []
    if isinstance(feats, dict):
        return feats.get(feature_id)
    for f in feats:
        if isinstance(f, dict) and _feature_id(f) == feature_id:
            return f
    return None


def explain_feature(
    feature_id: str,
    measured: dict[str, Any] | None = None,
    lang: str = "en",
) -> str:
    """Human-readable explanation — measurement, not classification proof."""
    entry = feature_entry(feature_id) or {}
    name = entry.get("name_ru" if lang == "ru" else "name_en") or feature_id
    meaning = entry.get("scientific_meaning") or entry.get("meaning") or ""
    status = entry.get("status", "experimental")
    measured = measured or {}
    val = measured.get("value")
    unit = measured.get("unit") or entry.get("unit") or ""
    valid = measured.get("valid", True)
    unc = measured.get("uncertainty")
    reason = measured.get("reason_invalid") or ""
    excl = (measured.get("metadata") or {}).get("excluded_sample_count")

    if lang == "ru":
        parts = [f"Что измерено: {name}."]
        if meaning:
            parts.append(f"Смысл: {meaning}")
        if val is None and not valid:
            parts.append(f"Результат недоступен ({reason or 'нет данных'}). Ноль не подставляется.")
        else:
            parts.append(f"Результат: {val} {unit}".strip() + ".")
            if unc is not None:
                parts.append(f"Неопределённость: {unc}.")
            parts.append("Валидность: да." if valid else f"Валидность: нет ({reason}).")
        if excl is not None:
            parts.append(f"Исключено выборок: {excl}.")
        parts.append(f"Статус: {status}.")
        parts.append(
            "Это измерение совместимо с геометрическими гипотезами, "
            "но само по себе не подтверждает морфологический тип. "
            "Текущая классификация не изменена."
        )
        return " ".join(parts)

    parts = [f"What was measured: {name}."]
    if meaning:
        parts.append(f"Meaning: {meaning}")
    if val is None and not valid:
        parts.append(f"Result unavailable ({reason or 'no data'}). Zero is not substituted.")
    else:
        parts.append(f"Result: {val} {unit}".strip() + ".")
        if unc is not None:
            parts.append(f"Uncertainty: {unc}.")
        parts.append("Valid: yes." if valid else f"Valid: no ({reason}).")
    if excl is not None:
        parts.append(f"Excluded samples: {excl}.")
    parts.append(f"Status: {status}.")
    parts.append(
        "This measurement is compatible with geometric hypotheses but does not by itself "
        "confirm a morphology type. Current classification is unchanged."
    )
    return " ".join(parts)


def required_registry_fields() -> list[str]:
    return [
        "feature_id",
        "name_en",
        "name_ru",
        "scientific_meaning",
        "algorithm",
        "unit",
        "missing_value_policy",
        "uncertainty_method",
        "implementation_version",
        "status",
    ]


def validate_registry_completeness(registry: dict[str, Any] | None = None) -> list[str]:
    reg = registry or load_feature_registry_v2()
    feats = reg.get("features") or []
    if isinstance(feats, dict):
        items = [{"feature_id": k, **v} for k, v in feats.items()]
    else:
        items = list(feats)
    errors: list[str] = []
    req = required_registry_fields()
    default_contract = reg.get("input_signal_contract")
    for f in items:
        fid = _feature_id(f) or "<missing>"
        if "feature_id" not in f and "id" in f:
            f = {**f, "feature_id": f["id"]}
        for k in req:
            if k == "feature_id":
                if not _feature_id(f):
                    errors.append(f"{fid}: missing feature_id")
                continue
            if k not in f or f[k] in (None, ""):
                errors.append(f"{fid}: missing {k}")
        if not f.get("input_signal_contract") and not default_contract:
            errors.append(f"{fid}: missing input_signal_contract")
        if f.get("implementation_version") and f["implementation_version"] != FEATURE_VERSION:
            if f.get("status") not in ("disabled",):
                errors.append(f"{fid}: implementation_version != {FEATURE_VERSION}")
    return errors
