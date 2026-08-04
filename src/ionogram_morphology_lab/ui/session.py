"""Shared UI session state linking import → profile → cache → viewer → batch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.instrument_profiles.schema import load_profile, profiles_dir
from ionogram_morphology_lab.projects.model import AnalysisProject
from ionogram_morphology_lab.ui.active_source import (
    ActiveSourceSnapshot,
    invalidate_active_source_snapshot,
    rebuild_active_source_snapshot,
    resolve_active_source,
)


class SessionEvents(QObject):
    """Broadcasts session lifecycle so pages refresh without restart."""

    project_changed = Signal()
    active_mat_changed = Signal()
    frame_changed = Signal()
    profile_changed = Signal()
    inventory_changed = Signal()
    source_detached = Signal()
    cache_rebuilt = Signal()


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
    # Explicit MATLAB Studio hand-off for Method Comparison (never auto-inserted into Results).
    matlab_comparison_candidates: list[dict[str, Any]] = field(default_factory=list)
    background_task: str = ""
    # Feature Diagnostics / V2 shadow job marker (string; empty when idle)
    v2_job_status: str = ""
    # Cached source identity — full SHA computed once (import/background), reused for navigation
    _source_sha_cache: str = ""
    _source_sha_meta: tuple[str, int, int] | None = None
    # Phase 4B.2h — shared source service (one per session / active MAT)
    source_service: Any = None
    # Phase 4B.2k — immutable active-source snapshot + classification cache
    _active_source_snap: ActiveSourceSnapshot | None = None
    _source_classifications: dict = field(default_factory=dict)
    _snapshot_generation: int = 0
    events: SessionEvents = field(default_factory=SessionEvents)

    def __post_init__(self) -> None:
        if not isinstance(self.events, SessionEvents):
            self.events = SessionEvents()
        self.load_profile(self.settings.get("data", "default_profile_id", self.profile_id))
        try:
            from ionogram_morphology_lab.ui.source_service import SourceService

            self.source_service = SourceService(self)
        except Exception:
            self.source_service = None

    def _source_file_meta(self, path: Path) -> tuple[str, int, int] | None:
        try:
            st = path.stat()
            return (
                str(path.resolve()),
                int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                int(st.st_size),
            )
        except OSError:
            return None

    def remember_source_sha(self, path: Path | str, sha: str) -> None:
        p = Path(path)
        meta = self._source_file_meta(p)
        if meta is None or not sha:
            return
        self._source_sha_cache = sha
        self._source_sha_meta = meta
        try:
            from ionogram_morphology_lab.ui.fd_frame_loader import remember_source_sha as _rem

            _rem(p, sha)
        except Exception:
            pass

    def get_source_sha(self, *, allow_compute: bool = False) -> str:
        """Return source SHA without hashing on every call. Optionally compute once."""
        if self.active_mat is None or not self.active_mat.is_file():
            return ""
        meta = self._source_file_meta(self.active_mat)
        if meta is not None and self._source_sha_meta == meta and self._source_sha_cache:
            return self._source_sha_cache
        if self.frame_store is not None and getattr(self.frame_store, "source_sha256", ""):
            try:
                if self.frame_store.source_path.resolve() == self.active_mat.resolve():
                    self.remember_source_sha(self.active_mat, self.frame_store.source_sha256)
                    return self.frame_store.source_sha256
            except OSError:
                pass
        if not allow_compute:
            return self._source_sha_cache or ""
        from ionogram_morphology_lab.utils.hashing import sha256_file

        sha = sha256_file(self.active_mat)
        self.remember_source_sha(self.active_mat, sha)
        return sha

    def load_profile(self, profile_id: str) -> dict[str, Any]:
        path = profiles_dir() / f"{profile_id}.yaml"
        if not path.exists():
            path = profiles_dir() / "kfu_cyclone_2013_2014.yaml"
        prof = load_profile(path)
        self.profile_id = prof.profile_id
        self.profile = prof.to_dict()
        if self.project is not None:
            self.project.profile_id = self.profile_id
        invalidate_active_source_snapshot(self)
        self._source_classifications.clear()
        self.events.profile_changed.emit()
        return self.profile

    def set_active_mat(self, path: Path | None, *, emit: bool = True) -> None:
        """Set the single active MAT source (not inventory-only)."""
        self.active_mat = Path(path) if path is not None else None
        self.frame_store = None
        self.current_frame = 1
        self.v2_job_status = ""
        self._source_sha_cache = ""
        self._source_sha_meta = None
        invalidate_active_source_snapshot(self)
        if self.project is not None:
            self.project.active_source_path = str(self.active_mat) if self.active_mat else None
        # Rebuild once at activation so warm UI never re-inspects MAT.
        if self.active_mat is not None:
            try:
                rebuild_active_source_snapshot(self)
            except Exception:
                pass
        if emit:
            self.events.active_mat_changed.emit()

    def detach_active_mat(self, *, emit: bool = True) -> None:
        """Remove MAT from active session context only — never delete the file."""
        self.active_mat = None
        self.frame_store = None
        self.current_frame = 1
        self.v2_job_status = ""
        self._source_sha_cache = ""
        self._source_sha_meta = None
        invalidate_active_source_snapshot(self)
        if self.project is not None:
            self.project.active_source_path = None
        if emit:
            self.events.source_detached.emit()
            self.events.active_mat_changed.emit()

    def add_to_inventory(self, path: Path, *, make_active: bool = True) -> None:
        p = Path(path)
        if p not in self.selected_mats:
            self.selected_mats.append(p)
        if self.project is not None:
            sp = str(p)
            if sp not in self.project.source_paths:
                self.project.source_paths.append(sp)
        # Drop stale classification for this path so rebuild re-inventories once.
        try:
            from ionogram_morphology_lab.ui.active_source import _norm_path_key

            self._source_classifications.pop(_norm_path_key(p), None)
        except Exception:
            pass
        invalidate_active_source_snapshot(self)
        self.events.inventory_changed.emit()
        if make_active:
            self.set_active_mat(p)

    def remove_inventory_entry(self, path: Path) -> None:
        """Remove project inventory entry only — never deletes the physical MAT."""
        p = Path(path)
        self.selected_mats = [x for x in self.selected_mats if x != p and x.resolve() != p.resolve()]
        if self.project is not None:
            self.project.source_paths = [
                s for s in self.project.source_paths
                if Path(s) != p and (not Path(s).exists() or Path(s).resolve() != p.resolve())
            ]
        if self.active_mat is not None and (
            self.active_mat == p or (self.active_mat.exists() and p.exists() and self.active_mat.resolve() == p.resolve())
        ):
            self.detach_active_mat(emit=False)
        self.events.inventory_changed.emit()
        self.events.active_mat_changed.emit()

    def set_current_frame(self, frame: int, *, emit: bool = True) -> None:
        self.current_frame = max(1, int(frame))
        if emit:
            self.events.frame_changed.emit()

    def ensure_store(self) -> FrameStore:
        if self.active_mat is None:
            raise RuntimeError("no_active_mat")
        if self.frame_store is not None and self.frame_store.source_path == self.active_mat.resolve():
            return self.frame_store
        cache_root = self.settings.cache_dir()
        known = self.get_source_sha(allow_compute=False)
        self.frame_store = FrameStore(
            self.active_mat,
            self.profile,
            cache_root=cache_root,
            prefetch_radius=int(self.settings.get("viewer", "prefetch_count", 2)),
            lru_capacity=int(self.settings.get("performance", "lru_capacity", 16)),
            source_sha256=known or None,
        )
        if self.frame_store.source_sha256:
            self.remember_source_sha(self.active_mat, self.frame_store.source_sha256)
        # Enrich existing snapshot from FrameStore — do not reopen MAT inventory.
        try:
            from dataclasses import replace as _replace

            from ionogram_morphology_lab.ui.active_source import paths_equal

            snap = self._active_source_snap
            if snap is not None and paths_equal(snap.mat_path, self.active_mat):
                meta = getattr(self.frame_store, "meta", None) or {}
                shape = meta.get("shape") or getattr(self.frame_store, "shape", None)
                shape_s = "×".join(str(int(x)) for x in shape) if shape is not None else snap.shape
                zroot = getattr(self.frame_store, "zarr_root", None) or getattr(
                    self.frame_store, "cache_dir", None
                )
                self._active_source_snap = _replace(
                    snap,
                    shape=shape_s or snap.shape,
                    dtype=str(meta.get("dtype") or getattr(self.frame_store, "dtype", "") or snap.dtype),
                    frame_count=int(self.frame_store.n_frames()) if hasattr(self.frame_store, "n_frames") else snap.frame_count,
                    cache_status="ready",
                    viewer_cache_state="ready",
                    zarr_root=str(zroot) if zroot else snap.zarr_root,
                    source_sha256=self.frame_store.source_sha256 or snap.source_sha256,
                    sha_status="ok" if (self.frame_store.source_sha256 or snap.source_sha256) else snap.sha_status,
                    readiness="ready",
                    status=snap.status if snap.status.value == "ready" else snap.status,
                )
                from ionogram_morphology_lab.ui.active_source import SourceStatus

                self._active_source_snap = _replace(
                    self._active_source_snap, status=SourceStatus.READY, readiness="ready"
                )
            elif snap is None:
                rebuild_active_source_snapshot(self)
        except Exception:
            pass
        return self.frame_store

    def has_real_import(self) -> bool:
        return self.active_mat is not None and self.active_mat.exists()

    def has_active_source(self) -> bool:
        return self.has_real_import()

    def active_source_snapshot(self, *, force_rebuild: bool = False) -> ActiveSourceSnapshot:
        return resolve_active_source(self, force_rebuild=force_rebuild)

    def refresh_active_source_snapshot(self) -> ActiveSourceSnapshot:
        """Explicit user Refresh Source — may open/stat MAT."""
        self._source_classifications.clear()
        invalidate_active_source_snapshot(self)
        return rebuild_active_source_snapshot(self)

    def restore_inventory_from_project(self) -> None:
        """Restore selected_mats / active_mat from persisted project fields."""
        if self.project is None:
            return
        restored: list[Path] = []
        for s in self.project.source_paths or []:
            p = Path(s)
            restored.append(p)
        self.selected_mats = restored
        active = getattr(self.project, "active_source_path", None)
        if active:
            ap = Path(active)
            if ap.is_file():
                self.set_active_mat(ap, emit=False)
                return
        # Fallback: first existing inventory path
        for p in restored:
            if p.is_file():
                self.set_active_mat(p, emit=False)
                return
        self.set_active_mat(None, emit=False)
