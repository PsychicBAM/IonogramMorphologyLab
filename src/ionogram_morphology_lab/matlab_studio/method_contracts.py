"""Declared expected outputs for built-in / library MATLAB methods (metadata only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, load_manifest
from ionogram_morphology_lab.utils.paths import app_root

OutputKind = Literal[
    "scalar_value",
    "registered_feature",
    "scientific_candidate",
    "table",
    "matrix",
    "diagnostic_image",
    "figure",
    "output_file",
    "warning_only",
]


@dataclass
class MethodOutputContract:
    method_id: str
    name_en: str
    name_ru: str
    category: str = ""
    script_type: str = "frame_analysis"
    scientific_status: str = "teaching"
    expected_kinds: list[str] = field(default_factory=list)
    diagnostic_image_expected: bool = False
    parameter_only: bool = False
    summary_en: str = ""
    summary_ru: str = ""
    limitations_en: str = ""
    limitations_ru: str = ""
    version: str = "11.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "name_en": self.name_en,
            "name_ru": self.name_ru,
            "category": self.category,
            "script_type": self.script_type,
            "scientific_status": self.scientific_status,
            "expected_kinds": list(self.expected_kinds),
            "diagnostic_image_expected": self.diagnostic_image_expected,
            "parameter_only": self.parameter_only,
            "summary_en": self.summary_en,
            "summary_ru": self.summary_ru,
            "limitations_en": self.limitations_en,
            "limitations_ru": self.limitations_ru,
            "version": self.version,
        }


# Defaults by script_type / category when per-method YAML fields are empty.
_CATEGORY_DEFAULTS: dict[str, dict[str, Any]] = {
    "rendering": {
        "kinds": ["figure", "diagnostic_image", "output_file"],
        "image": True,
        "en": "Creates diagnostic / teaching figures in the run output folder.",
        "ru": "Создаёт диагностические / учебные рисунки в папке запуска.",
    },
    "trace_detection": {
        "kinds": ["matrix", "registered_feature", "diagnostic_image", "figure"],
        "image": True,
        "en": "Expected: trace/interference masks and optional overlay figure.",
        "ru": "Ожидается: маски трассы/помех и опциональный оверлей.",
    },
    "interference": {
        "kinds": ["matrix", "registered_feature", "diagnostic_image", "figure"],
        "image": True,
        "en": "Expected: interference mask + overlay figure.",
        "ru": "Ожидается: маска помех и оверлей.",
    },
    "spread_f": {
        "kinds": ["scientific_candidate", "registered_feature", "diagnostic_image", "figure"],
        "image": True,
        "en": "Expected: morphology candidate evidence + highlighted spread regions.",
        "ru": "Ожидается: кандидат морфологии и выделенные области рассеяния.",
    },
    "layer_detection": {
        "kinds": ["scientific_candidate", "registered_feature", "diagnostic_image"],
        "image": True,
        "en": "Expected: layer region candidate; diagnostic overlay when applicable.",
        "ru": "Ожидается: кандидат области слоя; оверлей при необходимости.",
    },
    "parameters": {
        "kinds": ["scalar_value", "scientific_candidate", "registered_feature"],
        "image": False,
        "parameter_only": True,
        "en": "Returns a numeric candidate estimate; does not create a separate image by default.",
        "ru": "Возвращает численную кандидатную оценку и не создаёт отдельное изображение.",
    },
    "core": {
        "kinds": ["matrix", "output_file", "table"],
        "image": False,
        "en": "Core I/O helpers: load/validate/export; figures only if explicitly rendered.",
        "ru": "Базовые I/O-помощники: загрузка/проверка/экспорт; рисунки только при явной отрисовке.",
    },
    "comparison": {
        "kinds": ["table", "scalar_value", "figure"],
        "image": True,
        "en": "Expected: similarity metrics and a comparison figure.",
        "ru": "Ожидается: метрики сходства и рисунок сравнения.",
    },
    "teaching": {
        "kinds": ["output_file", "warning_only"],
        "image": False,
        "en": "Teaching script: outputs are explicitly documented in the method header.",
        "ru": "Учебный скрипт: выходы явно описаны в заголовке метода.",
    },
}

_METHOD_OVERRIDES: dict[str, dict[str, Any]] = {
    "iml_estimate_foE_candidate": {"kinds": ["scalar_value", "scientific_candidate"], "image": False, "parameter_only": True},
    "iml_estimate_foF2_candidate": {"kinds": ["scalar_value", "scientific_candidate"], "image": False, "parameter_only": True},
    "iml_estimate_candidate_frequency": {"kinds": ["scalar_value", "scientific_candidate"], "image": False, "parameter_only": True},
    "iml_estimate_candidate_range": {"kinds": ["scalar_value", "scientific_candidate"], "image": False, "parameter_only": True},
    "iml_measure_candidate_snr": {"kinds": ["scalar_value", "registered_feature"], "image": False, "parameter_only": True},
    "iml_render_raw_ionogram": {"kinds": ["figure", "diagnostic_image", "output_file"], "image": True},
    "iml_create_contact_sheet": {"kinds": ["figure", "output_file"], "image": True},
    "iml_trace_ridge_candidate": {"kinds": ["matrix", "registered_feature", "diagnostic_image"], "image": True},
    "iml_compare_trace_methods": {"kinds": ["table", "figure", "scalar_value"], "image": True},
}


def _manifests_dir() -> Path:
    return app_root() / "matlab_builtin" / "manifests"


def _load_category_index() -> dict[str, dict[str, Any]]:
    """Map method_id -> category manifest metadata."""
    index: dict[str, dict[str, Any]] = {}
    root = _manifests_dir()
    if not root.exists():
        return index
    for path in sorted(root.glob("*.iml-matlab.yaml")):
        category = path.name.replace(".iml-matlab.yaml", "")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — some shipping YAMLs have unquoted colons
            # Fall back: harvest method ids from a plain "methods:" block.
            text = path.read_text(encoding="utf-8", errors="replace")
            methods = []
            in_methods = False
            for line in text.splitlines():
                if line.strip() == "methods:":
                    in_methods = True
                    continue
                if in_methods:
                    if line.startswith("  - "):
                        methods.append(line.strip()[2:].strip())
                    elif line.strip() and not line.startswith(" "):
                        break
            data = {"methods": methods, "name_en": category, "name_ru": category}
        for method_id in data.get("methods") or []:
            index[str(method_id)] = {
                "category": category,
                "plugin_id": data.get("plugin_id", ""),
                "version": str(data.get("version", "11.0.0")),
                "scientific_status": data.get("scientific_status", "teaching"),
                "script_type": data.get("script_type", "frame_analysis"),
                "limitations_en": data.get("limitations_en", ""),
                "limitations_ru": data.get("limitations_ru", ""),
                "name_en": data.get("name_en", method_id),
                "name_ru": data.get("name_ru", method_id),
                "expected_outputs": data.get("expected_outputs") or [],
                "output_plots": data.get("output_plots") or [],
            }
    return index


def contract_from_manifest(manifest: ScriptManifest, method_id: str | None = None) -> MethodOutputContract:
    mid = method_id or manifest.plugin_id
    kinds = list(manifest.expected_outputs or [])
    image = bool(manifest.output_plots) or any(
        k in ("figure", "diagnostic_image", "output_plots") for k in kinds
    )
    parameter_only = manifest.script_type in ("feature_extraction",) and not image
    if not kinds:
        return get_method_contract(mid)
    return MethodOutputContract(
        method_id=mid,
        name_en=manifest.name_en or mid,
        name_ru=manifest.name_ru or mid,
        script_type=manifest.script_type,
        scientific_status=manifest.scientific_status,
        expected_kinds=kinds,
        diagnostic_image_expected=image,
        parameter_only=parameter_only and not image,
        summary_en=manifest.description_en or "",
        summary_ru=manifest.description_ru or "",
        limitations_en=manifest.limitations_en,
        limitations_ru=manifest.limitations_ru,
        version=manifest.version,
    )


def get_method_contract(method_id: str, manifest_path: Path | str | None = None) -> MethodOutputContract:
    if manifest_path:
        try:
            return contract_from_manifest(load_manifest(manifest_path), method_id=method_id)
        except Exception:  # noqa: BLE001
            pass
    index = _load_category_index()
    meta = index.get(method_id, {})
    category = meta.get("category") or ""
    # Infer category from method_id prefixes when not in index.
    if not category:
        for prefix, cat in (
            ("iml_render", "rendering"),
            ("iml_create_contact", "rendering"),
            ("iml_trace", "trace_detection"),
            ("iml_extract", "trace_detection"),
            ("iml_compare_trace", "comparison"),
            ("iml_estimate_fo", "parameters"),
            ("iml_estimate_candidate", "parameters"),
            ("iml_measure", "parameters"),
            ("iml_detect", "layer_detection"),
            ("iml_load", "core"),
            ("iml_validate", "core"),
            ("iml_export", "core"),
        ):
            if method_id.startswith(prefix):
                category = cat
                break
    defaults = _CATEGORY_DEFAULTS.get(category, _CATEGORY_DEFAULTS["teaching"])
    override = _METHOD_OVERRIDES.get(method_id, {})
    kinds = list(override.get("kinds") or meta.get("expected_outputs") or defaults["kinds"])
    image = bool(override.get("image", defaults.get("image", False)))
    parameter_only = bool(override.get("parameter_only", defaults.get("parameter_only", False)))
    return MethodOutputContract(
        method_id=method_id,
        name_en=str(meta.get("name_en") or method_id),
        name_ru=str(meta.get("name_ru") or method_id),
        category=category or "custom",
        script_type=str(meta.get("script_type") or "frame_analysis"),
        scientific_status=str(meta.get("scientific_status") or "teaching"),
        expected_kinds=kinds,
        diagnostic_image_expected=image,
        parameter_only=parameter_only,
        summary_en=str(defaults.get("en", "")),
        summary_ru=str(defaults.get("ru", "")),
        limitations_en=str(meta.get("limitations_en") or ""),
        limitations_ru=str(meta.get("limitations_ru") or ""),
        version=str(meta.get("version") or "11.0.0"),
    )


def format_expected_output(contract: MethodOutputContract, lang: str = "en") -> str:
    ru = lang == "ru"
    title = "Ожидаемый результат метода" if ru else "Expected Method Output"
    kinds_labels = {
        "scalar_value": ("скалярное значение", "scalar value"),
        "registered_feature": ("зарегистрированный признак", "registered feature"),
        "scientific_candidate": ("научный кандидат", "scientific candidate"),
        "table": ("таблица", "table"),
        "matrix": ("матрица", "matrix"),
        "diagnostic_image": ("диагностическое изображение", "diagnostic image"),
        "figure": ("рисунок", "figure"),
        "output_file": ("выходной файл", "output file"),
        "warning_only": ("только предупреждение", "warning-only result"),
    }
    kind_lines = []
    for kind in contract.expected_kinds:
        label = kinds_labels.get(kind, (kind, kind))[0 if ru else 1]
        kind_lines.append(f"• {label}")
    summary = contract.summary_ru if ru else contract.summary_en
    if contract.parameter_only:
        extra = (
            "Этот метод возвращает численную кандидатную оценку и не создаёт отдельное изображение."
            if ru
            else "This method returns a numeric candidate estimate and does not create a separate image."
        )
    elif contract.diagnostic_image_expected:
        extra = (
            "Диагностический рисунок ожидается и появится во вкладке «Рисунки», если метод его создаст."
            if ru
            else "A diagnostic figure is expected and will appear under Figures when the method creates one."
        )
    else:
        extra = (
            "Не каждый метод MATLAB создаёт изображение — смотрите список ожидаемых выходов."
            if ru
            else "Not every MATLAB method creates an image — see the expected-output list."
        )
    return (
        f"{title}\n"
        f"{contract.method_id} v{contract.version}\n"
        f"{summary}\n\n"
        + ("Ожидаемые типы выхода:\n" if ru else "Expected output kinds:\n")
        + "\n".join(kind_lines)
        + f"\n\n{extra}"
    )


def classify_scientific_run_status(
    *,
    job_status: str,
    payload: dict[str, Any],
) -> str:
    """Distinguish scientific usefulness beyond process exit code."""
    if job_status in ("cancelled", "canceled"):
        return "execution_cancelled"
    if job_status in ("timeout", "timed_out"):
        return "execution_timed_out"
    if job_status in ("failed", "error") or payload.get("status") in ("error", "failed"):
        return "execution_failed"
    outputs = dict(payload.get("outputs") or {})
    files = list(payload.get("output_files") or [])
    features = outputs.get("registered_features") or outputs.get("features") or []
    candidates = outputs.get("scientific_candidates") or outputs.get("candidates") or []
    values = outputs.get("values") or outputs.get("scalars") or []
    if features or candidates or values:
        return "completed_with_registered_output"
    if files:
        return "completed_with_files_only"
    return "completed_with_no_registered_output"


def count_contracts() -> dict[str, int]:
    index = _load_category_index()
    ids = sorted(set(index) | set(_METHOD_OVERRIDES))
    with_image = 0
    values_only = 0
    for mid in ids:
        c = get_method_contract(mid)
        if c.diagnostic_image_expected:
            with_image += 1
        if c.parameter_only or (
            not c.diagnostic_image_expected
            and any(k in c.expected_kinds for k in ("scalar_value", "scientific_candidate"))
        ):
            values_only += 1
    return {
        "declared": len(ids),
        "diagnostic_figures": with_image,
        "values_only": values_only,
    }
