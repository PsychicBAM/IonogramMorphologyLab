"""MATLAB plugin registry — enable/disable without modifying application source."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.matlab_studio.manifest import (
    ScriptManifest,
    load_manifest,
    validate_manifest,
)
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


@dataclass
class RegisteredPlugin:
    plugin_id: str
    manifest_path: str
    enabled: bool = True
    role: str = "custom"  # diagnostic|feature|renderer|classifier|comparator|exporter|batch|custom
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PluginRegistry:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else app_root() / "config" / "matlab_plugins.json"
        self.plugins: dict[str, RegisteredPlugin] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.plugins = {k: RegisteredPlugin(**v) for k, v in data.items()}
        else:
            self.plugins = {}

    def save(self) -> None:
        ensure_dir(self.path.parent)
        payload = {k: v.to_dict() for k, v in self.plugins.items()}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def register(self, manifest_path: Path | str, role: str = "custom", enabled: bool = True) -> RegisteredPlugin:
        man = load_manifest(manifest_path)
        errs = validate_manifest(man)
        if errs:
            raise ValueError("manifest_invalid:" + ",".join(errs))
        if man.scientific_status == "imported_unverified":
            # allowed, but never presented as verified
            pass
        plug = RegisteredPlugin(
            plugin_id=man.plugin_id,
            manifest_path=str(manifest_path),
            enabled=enabled,
            role=role,
        )
        self.plugins[man.plugin_id] = plug
        self.save()
        return plug

    def enable(self, plugin_id: str) -> None:
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True
            self.plugins[plugin_id].last_error = ""
            self.save()

    def disable(self, plugin_id: str, reason: str = "") -> None:
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False
            self.plugins[plugin_id].last_error = reason
            self.save()

    def enabled_plugins(self) -> list[RegisteredPlugin]:
        return [p for p in self.plugins.values() if p.enabled]

    def get_manifest(self, plugin_id: str) -> ScriptManifest | None:
        p = self.plugins.get(plugin_id)
        if not p:
            return None
        return load_manifest(p.manifest_path)
