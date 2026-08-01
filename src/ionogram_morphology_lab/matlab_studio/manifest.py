"""MATLAB script / plugin manifest (.iml-matlab.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

SCRIPT_TYPES = (
    "frame_analysis",
    "sequence_analysis",
    "file_analysis",
    "folder_analysis",
    "rendering",
    "feature_extraction",
    "classifier",
    "comparison",
    "export",
    "teaching_demo",
    "custom",
)

SCIENTIFIC_STATUSES = (
    "built_in_verified",
    "project_verified",
    "user_tested",
    "imported_unverified",
    "incompatible",
    "disabled",
    "example",
    "teaching",
)


@dataclass
class ScriptManifest:
    plugin_id: str
    name_ru: str
    name_en: str
    description_ru: str = ""
    description_en: str = ""
    version: str = "0.1.0"
    author: str = ""
    institution: str = ""
    entrypoint: str = "main.m"
    script_type: str = "frame_analysis"
    supported_profiles: list[str] = field(default_factory=lambda: ["*"])
    supported_matrix_shapes: list[str] = field(default_factory=list)
    required_variables: list[str] = field(default_factory=list)
    optional_variables: list[str] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    output_plots: list[str] = field(default_factory=list)
    MATLAB_release: str = ""
    required_toolboxes: list[str] = field(default_factory=list)
    Octave_compatible: bool = False
    timeout: int = 120
    rights: str = "user"
    citation: str = ""
    scientific_status: str = "imported_unverified"
    limitations_ru: str = "Пользовательский код не считается автоматически научно верифицированным."
    limitations_en: str = "Imported user code is not automatically scientifically verified."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_manifest(path: Path | str) -> ScriptManifest:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    known = ScriptManifest.__dataclass_fields__
    return ScriptManifest(**{k: v for k, v in data.items() if k in known})


def save_manifest(manifest: ScriptManifest, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(manifest.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def validate_manifest(manifest: ScriptManifest) -> list[str]:
    errors: list[str] = []
    if not manifest.plugin_id:
        errors.append("missing_plugin_id")
    if not manifest.entrypoint:
        errors.append("missing_entrypoint")
    if manifest.script_type not in SCRIPT_TYPES:
        errors.append(f"invalid_script_type:{manifest.script_type}")
    if manifest.scientific_status not in SCIENTIFIC_STATUSES:
        errors.append(f"invalid_scientific_status:{manifest.scientific_status}")
    if manifest.timeout <= 0:
        errors.append("invalid_timeout")
    return errors
