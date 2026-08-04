"""One long-lived source service per active MAT (Phase 4B.2h / 4B.2k).

Viewer, Diagnostics, Batch, Raw Signals, and MATLAB share the session FrameStore
through this service — pages must not open independent MAT/Zarr handles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.cache.frame_store import FrameStore
from ionogram_morphology_lab.ui.active_source import paths_equal
from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

# Process-wide diagnostics (Phase 4B.2k)
_SOURCE_SERVICE_INSTANCES = 0
_ADAPTER_CREATION_COUNT = 0
_MAT_LOGICAL_OPEN_COUNT = 0
_VARIABLE_INVENTORY_SCAN_COUNT = 0
_FRAME_STORE_INSTANCES = 0


def bump_adapter_creation(n: int = 1) -> None:
    global _ADAPTER_CREATION_COUNT
    _ADAPTER_CREATION_COUNT += n
    prof = get_profiler()
    if prof is not None:
        prof.bump("adapter_creation_count", n)


def bump_variable_inventory_scan(n: int = 1) -> None:
    global _VARIABLE_INVENTORY_SCAN_COUNT
    _VARIABLE_INVENTORY_SCAN_COUNT += n
    prof = get_profiler()
    if prof is not None:
        prof.bump("variable_inventory_scan_count", n)


def bump_mat_logical_open(n: int = 1) -> None:
    global _MAT_LOGICAL_OPEN_COUNT
    _MAT_LOGICAL_OPEN_COUNT += n
    prof = get_profiler()
    if prof is not None:
        prof.bump("MAT_logical_open_count", n)


def bump_frame_store_instances(n: int = 1) -> None:
    global _FRAME_STORE_INSTANCES
    _FRAME_STORE_INSTANCES += n
    prof = get_profiler()
    if prof is not None:
        prof.bump("frame_store_instances", n)


def global_source_counters() -> dict[str, int]:
    return {
        "source_service_instances": _SOURCE_SERVICE_INSTANCES,
        "adapter_creation_count": _ADAPTER_CREATION_COUNT,
        "MAT_logical_open_count": _MAT_LOGICAL_OPEN_COUNT,
        "variable_inventory_scan_count": _VARIABLE_INVENTORY_SCAN_COUNT,
        "frame_store_instances": _FRAME_STORE_INSTANCES,
    }


@dataclass
class SourceServiceCounters:
    active_source_service_instances: int = 0
    MAT_open_count: int = 0
    MAT_logical_open_count: int = 0
    Zarr_open_count: int = 0
    frame_requests: int = 0
    memory_hits: int = 0
    Zarr_hits: int = 0
    disk_fallbacks: int = 0
    source_reload_count: int = 0
    adapter_creation_count: int = 0
    variable_inventory_scan_count: int = 0
    frame_store_instances: int = 0

    def as_dict(self) -> dict[str, int]:
        g = global_source_counters()
        return {
            "active_source_service_instances": self.active_source_service_instances,
            "source_service_instances": g["source_service_instances"],
            "MAT_open_count": self.MAT_open_count,
            "MAT_logical_open_count": self.MAT_logical_open_count + g["MAT_logical_open_count"],
            "Zarr_open_count": self.Zarr_open_count,
            "frame_requests": self.frame_requests,
            "memory_hits": self.memory_hits,
            "Zarr_hits": self.Zarr_hits,
            "disk_fallbacks": self.disk_fallbacks,
            "source_reload_count": self.source_reload_count,
            "adapter_creation_count": self.adapter_creation_count + g["adapter_creation_count"],
            "variable_inventory_scan_count": (
                self.variable_inventory_scan_count + g["variable_inventory_scan_count"]
            ),
            "frame_store_instances": self.frame_store_instances + g["frame_store_instances"],
        }


@dataclass
class SourceService:
    """Thin façade over AppSession.frame_store with open/request counters."""

    session: Any
    counters: SourceServiceCounters = field(default_factory=SourceServiceCounters)
    _bound_path: Path | None = None

    def __post_init__(self) -> None:
        global _SOURCE_SERVICE_INSTANCES
        self.counters.active_source_service_instances = 1
        _SOURCE_SERVICE_INSTANCES += 1

    @property
    def frame_store(self) -> FrameStore | None:
        return getattr(self.session, "frame_store", None)

    def source_path(self) -> Path | None:
        mat = getattr(self.session, "active_mat", None)
        return Path(mat) if mat is not None else None

    def source_sha(self, *, allow_compute: bool = False) -> str:
        return str(self.session.get_source_sha(allow_compute=allow_compute) or "")

    def ensure_bound(self) -> FrameStore | None:
        """Reuse session store; do not create a second FrameStore for the same MAT."""
        mat = self.source_path()
        store = self.frame_store
        if mat is None:
            return None
        if store is not None and paths_equal(getattr(store, "source_path", None), mat):
            self._bound_path = mat
            return store
        # Only create via session.ensure_store — single owner
        self.counters.source_reload_count += 1
        self.counters.MAT_open_count += 1
        self.counters.MAT_logical_open_count += 1
        bump_mat_logical_open()
        bump_frame_store_instances()
        self.counters.frame_store_instances += 1
        prof = get_profiler()
        if prof is not None:
            prof.bump("source_reload_count")
            prof.bump("MAT_open_count")
        store = self.session.ensure_store()
        self._bound_path = mat
        try:
            if store.status().valid:
                self.counters.Zarr_open_count += 1
                if prof is not None:
                    prof.bump("Zarr_open_count")
        except Exception:
            pass
        return store

    def get_existing_store(self) -> FrameStore | None:
        """Return valid store without opening MAT/Zarr."""
        store = self.frame_store
        mat = self.source_path()
        if store is None or mat is None:
            return None
        try:
            if not paths_equal(getattr(store, "source_path", None), mat):
                return None
            if not store.status().valid:
                return None
        except Exception:
            return None
        return store

    def note_frame_path(self, path_kind: str) -> None:
        self.counters.frame_requests += 1
        prof = get_profiler()
        if prof is not None:
            prof.bump("frame_requests")
        key_map = {
            "memory": "memory_hits",
            "framestore": "memory_hits",
            "zarr": "Zarr_hits",
            "loaded_mat": "disk_fallbacks",
            "disk": "disk_fallbacks",
            "disk_fallback": "disk_fallbacks",
        }
        attr = key_map.get(path_kind)
        if attr:
            setattr(self.counters, attr, getattr(self.counters, attr) + 1)
            if prof is not None:
                prof.bump(attr)

    def close(self) -> None:
        global _SOURCE_SERVICE_INSTANCES
        self.session.frame_store = None
        self._bound_path = None
        self.counters.active_source_service_instances = 0
        if _SOURCE_SERVICE_INSTANCES > 0:
            _SOURCE_SERVICE_INSTANCES -= 1
