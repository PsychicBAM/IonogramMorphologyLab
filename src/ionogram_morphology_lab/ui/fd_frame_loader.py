"""Async frame loading for Feature Diagnostics — FrameStore-first (Phase 4B.2g)."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute, mapping_status
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
from ionogram_morphology_lab.ui.frame_diagnostic_context import (
    build_frame_context,
    next_request_generation_id,
)
from ionogram_morphology_lab.utils.hashing import sha256_file

# Process-level MAT matrix cache: path → (mtime_ns, size, data, variable)
_MATRIX_CACHE: dict[str, tuple[int, int, Any, str]] = {}
# Validated source SHA cache: path → (mtime_ns, size, sha)
_SOURCE_SHA_CACHE: dict[str, tuple[int, int, str]] = {}
# Navigation stats for audits
_NAV_STATS = {
    "mat_opens": 0,
    "sha_calcs": 0,
    "framestore_hits": 0,
    "memory_hits": 0,
    "zarr_hits": 0,
    "disk_fallback": 0,
}


def nav_stats() -> dict[str, int]:
    return dict(_NAV_STATS)


def reset_nav_stats() -> None:
    for k in _NAV_STATS:
        _NAV_STATS[k] = 0


def frame_sha256(arr: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(arr))
    return hashlib.sha256(a.tobytes()).hexdigest()


def _file_meta(path: Path) -> tuple[int, int]:
    st = path.stat()
    return int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), int(st.st_size)


def peek_cached_source_sha(path: Path | str) -> str | None:
    """Return cached SHA without hashing, or None if missing/stale."""
    p = Path(path)
    try:
        meta = _file_meta(p)
    except OSError:
        return None
    hit = _SOURCE_SHA_CACHE.get(str(p.resolve()))
    if hit is not None and hit[0] == meta[0] and hit[1] == meta[1]:
        return hit[2]
    return None


def remember_source_sha(path: Path | str, sha: str) -> None:
    p = Path(path)
    try:
        meta = _file_meta(p)
        _SOURCE_SHA_CACHE[str(p.resolve())] = (meta[0], meta[1], sha)
    except OSError:
        pass


def cached_source_sha(path: Path | str, *, allow_compute: bool = True) -> str:
    """Reuse SHA-256 unless file mtime/size changed. Optionally skip compute."""
    p = Path(path)
    meta = _file_meta(p)
    hit = _SOURCE_SHA_CACHE.get(str(p.resolve()))
    if hit is not None and hit[0] == meta[0] and hit[1] == meta[1]:
        return hit[2]
    if not allow_compute:
        return ""
    _NAV_STATS["sha_calcs"] += 1
    sha = sha256_file(p)
    _SOURCE_SHA_CACHE[str(p.resolve())] = (meta[0], meta[1], sha)
    return sha


def cached_amplitude_matrix(path: Path | str, variable: str):
    p = Path(path)
    key = str(p.resolve())
    meta = _file_meta(p)
    hit = _MATRIX_CACHE.get(key)
    if hit is not None and hit[0] == meta[0] and hit[1] == meta[1] and hit[3] == variable:
        return hit[2]
    _NAV_STATS["mat_opens"] += 1
    loaded = load_amplitude_matrix(p, variable=variable)
    _MATRIX_CACHE[key] = (meta[0], meta[1], loaded, variable)
    return loaded


def clear_fd_matrix_caches() -> None:
    _MATRIX_CACHE.clear()
    _SOURCE_SHA_CACHE.clear()


class FrameLoadWorker(QThread):
    """Load one numeric frame off the UI thread (FrameStore → memory → MAT)."""

    finished_ok = Signal(dict)
    failed = Signal(dict)
    cancelled = Signal(dict)

    def __init__(
        self,
        *,
        mat_path: Path,
        frame_index: int,
        profile: dict[str, Any],
        profile_id: str,
        signal_contract_id: str,
        n_frames: int = 1440,
        request_generation_id: str | None = None,
        known_source_sha: str = "",
        frame_store=None,
        parent=None,
    ):
        super().__init__(parent)
        self.mat_path = Path(mat_path)
        self.frame_index = int(frame_index)
        self.profile = profile or {}
        self.profile_id = profile_id
        self.signal_contract_id = signal_contract_id
        self.n_frames = int(n_frames)
        self.request_generation_id = request_generation_id or next_request_generation_id()
        self.known_source_sha = known_source_sha
        self.frame_store = frame_store
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: N802
        gen = self.request_generation_id
        try:
            t0 = time.perf_counter()
            if self._cancel:
                self.cancelled.emit({"request_generation_id": gen})
                return

            # Source SHA: never hash full MAT during navigation if known/cached
            source_sha = self.known_source_sha or peek_cached_source_sha(self.mat_path) or ""
            if self.frame_store is not None and getattr(self.frame_store, "source_sha256", ""):
                source_sha = source_sha or str(self.frame_store.source_sha256)
                remember_source_sha(self.mat_path, source_sha)
            if not source_sha:
                # Last resort — background-safe here (worker thread), still counted
                source_sha = cached_source_sha(self.mat_path, allow_compute=True)

            if self._cancel:
                self.cancelled.emit({"request_generation_id": gen})
                return

            variable = str(self.profile.get("amplitude_variable_name") or "Amp_all")
            height = int(self.profile.get("height_bins") or 256)
            width = int(self.profile.get("frequency_bins") or 400)
            source_path_used = "disk_fallback"
            raw: np.ndarray | None = None

            # 1) FrameStore LRU / Zarr
            store = self.frame_store
            if store is not None:
                try:
                    st = store.status()
                    if st.valid:
                        before_hits = int(store.stats.get("cache_hits", 0))
                        raw = np.asarray(store.get_frame(self.frame_index, prefetch=True))
                        after_hits = int(store.stats.get("cache_hits", 0))
                        if after_hits > before_hits:
                            source_path_used = "memory"
                            _NAV_STATS["memory_hits"] += 1
                        else:
                            source_path_used = "zarr"
                            _NAV_STATS["zarr_hits"] += 1
                        _NAV_STATS["framestore_hits"] += 1
                except Exception:
                    raw = None

            # 2) In-process loaded MAT
            if raw is None:
                loaded = cached_amplitude_matrix(self.mat_path, variable)
                if self._cancel:
                    self.cancelled.emit({"request_generation_id": gen})
                    return
                frame, _rng = extract_frame_consistent(
                    loaded.data, self.frame_index, height_bins=height, frequency_bins=width
                )
                raw = np.asarray(frame)
                source_path_used = "loaded_mat"
                _NAV_STATS["disk_fallback"] += 1

            raw_sha = frame_sha256(raw)
            tm = mapping_status(self.profile.get("time_mapping"))
            interpreted = format_hhmm(frame_to_minute(self.frame_index)) + (" *" if tm.available else "")
            if not tm.available:
                interpreted = "—"
            ctx = build_frame_context(
                mat_path=str(self.mat_path),
                source_sha256=source_sha,
                frame_index=self.frame_index,
                interpreted_time=interpreted,
                raw_frame_sha256=raw_sha,
                profile_id=self.profile_id,
                signal_contract_id=self.signal_contract_id,
                profile=self.profile,
                n_frames=self.n_frames,
                request_generation_id=gen,
            )
            if self._cancel:
                self.cancelled.emit({"request_generation_id": gen, "context": ctx.to_dict()})
                return
            self.finished_ok.emit(
                {
                    "request_generation_id": gen,
                    "context": ctx,
                    "raw": raw,
                    "frame_source_path": source_path_used,
                    "timings": {"total_s": time.perf_counter() - t0},
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit({"request_generation_id": gen, "error": str(exc)})
