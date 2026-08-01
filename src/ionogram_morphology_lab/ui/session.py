"""Shared UI session state linking import → profile → cache → viewer → batch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.instrument_profiles.schema import load_profile, profiles_dir
from ionogram_morphology_lab.projects.model import AnalysisProject


@dataclass
class AppSession:
    settings: SettingsStore
    project: AnalysisProject | None = None
    selected_mats: list[Path] = field(default_factory=list)
    active_mat: Path | None = None
    profile_id: str = "kfu_cyclone_2013_2014"
    profile: dict[str, Any] = field(default_factory=dict)
    frame_store: FrameStore | None = None
    current_frame: int = 1
    last_run_root: Path | None = None
    last_results: list[dict[str, Any]] = field(default_factory=list)
    last_audits: list[dict[str, Any]] = field(default_factory=list)
    background_task: str = ""

    def __post_init__(self) -> None:
        self.load_profile(self.settings.get("data", "default_profile_id", self.profile_id))

    def load_profile(self, profile_id: str) -> dict[str, Any]:
        path = profiles_dir() / f"{profile_id}.yaml"
        if not path.exists():
            path = profiles_dir() / "kfu_cyclone_2013_2014.yaml"
        prof = load_profile(path)
        self.profile_id = prof.profile_id
        self.profile = prof.to_dict()
        if self.project is not None:
            self.project.profile_id = self.profile_id
        return self.profile

    def set_active_mat(self, path: Path | None) -> None:
        self.active_mat = path
        self.frame_store = None
        self.current_frame = 1

    def ensure_store(self) -> FrameStore:
        if self.active_mat is None:
            raise RuntimeError("no_active_mat")
        if self.frame_store is not None and self.frame_store.source_path == self.active_mat.resolve():
            return self.frame_store
        cache_root = self.settings.cache_dir()
        self.frame_store = FrameStore(
            self.active_mat,
            self.profile,
            cache_root=cache_root,
            prefetch_radius=int(self.settings.get("viewer", "prefetch_count", 2)),
            lru_capacity=int(self.settings.get("performance", "lru_capacity", 16)),
        )
        return self.frame_store

    def has_real_import(self) -> bool:
        return self.active_mat is not None and self.active_mat.exists()
