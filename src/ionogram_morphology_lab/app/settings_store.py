"""Persistent application settings — v1.0 selectable analysis modes."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

ANALYSIS_MODES = ("fast_preview", "standard", "scientific_strict", "custom")

DEFAULT_SETTINGS: dict[str, Any] = {
    "general": {
        "language": "en",
        "theme": "system",
        "workspace_dir": "",
        "restore_last_project": True,
        "confirm_before_closing": True,
        "autosave_interval_sec": 120,
        "show_onboarding": True,
        "first_launch_done": False,
        "nav_collapsed": False,
        "window_geometry": "",
        "splitter_states": {},
    },
    "data": {
        "default_profile_id": "kfu_cyclone_2013_2014",
        "default_adapter": "auto",
        "recursive_folder_scan": True,
        "duplicate_detection": True,
        "calculate_source_sha": True,
        "strict_source_readonly": True,
    },
    "viewer": {
        "default_frame_step_minutes": 10,
        "navigation_jump_minutes": 10,
        "playback_speed": 2.0,
        "contact_layout": "5x5",
        "contact_interval_minutes": 10,
        "colormap": "jet",
        "amplitude_scale_mode": "percentile_display",
        "show_grid": False,
        "show_colorbar": True,
        "show_technical_frame_id": True,
        "preview_mode": "auto",
        "prefetch_count": 2,
    },
    "performance": {
        "worker_count": 1,
        "max_ram_mb": 4096,
        "cache_location": "",
        "max_cache_mb": 8192,
        "automatic_cache_creation": True,
        "cache_compression": True,
        "rendered_image_cache": True,
        "background_prefetch": True,
        "lru_capacity": 16,
    },
    "analysis": {
        "mode": "scientific_strict",
        "data_quality_audit": True,
        "trace_segmentation": True,
        "interference_diagnostics": True,
        "feature_extraction": True,
        "rule_engine": True,
        "reference_comparison": True,
        "ml_models_enabled": False,
        "abstention": True,
        "temporal_context": True,
        "disagreement": True,
        "ensemble": True,
    },
    "matlab": {
        "active_backend": "auto",
        "auto_detect": True,
        "matlab_executable": "",
        "octave_executable": "",
        "working_directory": "",
        "startup_script": "",
        "default_timeout_s": 120,
        "max_execution_s": 600,
        "max_output_mb": 512,
        "reuse_engine_session": True,
        "extra_paths": [],
        "env_vars": {},
        "first_trust_warning_ack": False,
        "builtin_trust_acknowledged": False,
    },
    "models": {
        "enabled_model_ids": [],
        "default_split": "by_date",
        "abstention_threshold": 0.45,
    },
    "reports": {
        "language": "both",
        "formats": ["csv", "json", "html", "markdown"],
        "include_technical_json": True,
        "include_diagnostic_figures": True,
        "include_bibliography": True,
        "include_reproducibility_manifest": True,
    },
    "privacy": {
        "telemetry_disabled": True,
        "network_disabled_by_default": True,
        "source_readonly": True,
        "protected_study_enabled": False,
        "protected_study_config_path": "",
    },
    "ux": {
        "interface_mode": "guided",  # guided | research | expert — UI complexity only
        "show_intros": True,
        "dismissed_intros": {},
        "show_workflow_on_home": True,
    },
    "advanced": {
        "show_developer_logs": False,
        "rule_pack_version": "IML1-0.1.0",
        "reference_pack_version": "IML1-0.1.0",
        "app_version": "1.1.1",
    },
}


class SettingsStore:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else app_root() / "config" / "user_settings.json"
        self.data = deepcopy(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self._merge(self.data, loaded)
        # Integrity invariants (not product restrictions)
        self.data["privacy"]["telemetry_disabled"] = True
        self.data["data"]["strict_source_readonly"] = True
        mode = self.data.get("analysis", {}).get("mode", "scientific_strict")
        if mode not in ANALYSIS_MODES:
            self.data["analysis"]["mode"] = "scientific_strict"

    def save(self) -> None:
        ensure_dir(self.path.parent)
        self.data["privacy"]["telemetry_disabled"] = True
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        self.data.setdefault(section, {})[key] = value

    def analysis_mode(self) -> str:
        return str(self.get("analysis", "mode", "scientific_strict"))

    def is_strict(self) -> bool:
        return self.analysis_mode() == "scientific_strict"

    def reset(self) -> None:
        lang = self.get("general", "language", "en")
        first = self.get("general", "first_launch_done", False)
        self.data = deepcopy(DEFAULT_SETTINGS)
        self.data["general"]["language"] = lang
        self.data["general"]["first_launch_done"] = first
        self.save()

    def export_to(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_from(self, path: Path | str) -> None:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        self.data = deepcopy(DEFAULT_SETTINGS)
        self._merge(self.data, loaded)
        self.data["privacy"]["telemetry_disabled"] = True
        self.save()

    @staticmethod
    def _merge(base: dict, overlay: dict) -> None:
        for k, v in overlay.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                SettingsStore._merge(base[k], v)
            else:
                base[k] = v

    def cache_dir(self) -> Path:
        custom = self.get("performance", "cache_location", "")
        if custom:
            return ensure_dir(custom)
        return ensure_dir(app_root() / "workspaces" / "_cache")
