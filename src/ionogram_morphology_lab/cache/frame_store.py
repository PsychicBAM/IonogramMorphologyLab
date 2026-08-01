"""Fast frame access: Zarr cache identity, LRU, prefetch — never modifies MAT."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.security import default_blocklist
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir

CACHE_FORMAT_VERSION = "iml2-zarr-frame-v1"


@dataclass
class CacheIdentity:
    source_sha256: str
    variable_name: str
    profile_id: str
    profile_version: str
    cache_format_version: str
    layout: str
    height_bins: int
    frequency_bins: int
    frames_per_file: int

    def key(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


@dataclass
class CacheStatus:
    present: bool
    valid: bool
    path: str | None = None
    reason: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


class LRUFrameCache:
    def __init__(self, capacity: int = 16):
        self.capacity = max(1, capacity)
        self._data: OrderedDict[int, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, frame_id: int) -> np.ndarray | None:
        with self._lock:
            if frame_id not in self._data:
                return None
            self._data.move_to_end(frame_id)
            return self._data[frame_id]

    def put(self, frame_id: int, frame: np.ndarray) -> None:
        with self._lock:
            self._data[frame_id] = frame
            self._data.move_to_end(frame_id)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


class FrameStore:
    """Session store for one MAT + profile: cache build, lazy frames, prefetch."""

    def __init__(
        self,
        source_path: Path | str,
        profile: dict[str, Any],
        cache_root: Path | str,
        variable_name: str | None = None,
        prefetch_radius: int = 2,
        lru_capacity: int = 16,
    ):
        self.source_path = default_blocklist().assert_allowed(source_path)
        self.profile = profile
        self.variable_name = variable_name or profile.get("amplitude_variable_name", "Amp_all")
        self.height_bins = int(profile.get("height_bins", 256))
        self.frequency_bins = int(profile.get("frequency_bins", 400))
        self.frames_per_file = int(profile.get("frames_per_file", 1440))
        self.cache_root = ensure_dir(cache_root)
        self.prefetch_radius = prefetch_radius
        self.lru = LRUFrameCache(lru_capacity)
        self.render_cache: OrderedDict[str, Path] = OrderedDict()
        self._zarr = None
        self._lock = threading.Lock()
        self._build_cancel = False
        self.stats = {"cache_hits": 0, "cache_misses": 0, "mat_loads": 0}
        self.source_sha256 = sha256_file(self.source_path) if self.source_path.is_file() else ""
        self.identity = CacheIdentity(
            source_sha256=self.source_sha256,
            variable_name=self.variable_name,
            profile_id=str(profile.get("profile_id", "unknown")),
            profile_version=str(profile.get("profile_verification_status", "unknown")),
            cache_format_version=CACHE_FORMAT_VERSION,
            layout=str(profile.get("matrix_layout", "frames_stacked_rows")),
            height_bins=self.height_bins,
            frequency_bins=self.frequency_bins,
            frames_per_file=self.frames_per_file,
        )
        self.cache_dir = self.cache_root / self.identity.key()

    def status(self) -> CacheStatus:
        prov_path = self.cache_dir / "provenance.json"
        zpath = self.cache_dir / "data.zarr"
        if not prov_path.exists() or not zpath.exists():
            return CacheStatus(False, False, str(self.cache_dir), "missing")
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        if prov.get("identity_key") != self.identity.key():
            return CacheStatus(True, False, str(self.cache_dir), "identity_mismatch", prov)
        if prov.get("source_sha256") != self.source_sha256:
            return CacheStatus(True, False, str(self.cache_dir), "source_hash_mismatch", prov)
        return CacheStatus(True, True, str(self.cache_dir), None, prov)

    def build_cache(
        self,
        progress_cb: Callable[[dict[str, Any]], None] | None = None,
        force: bool = False,
    ) -> CacheStatus:
        st = self.status()
        if st.valid and not force:
            self._open_zarr()
            return st
        if force and self.cache_dir.exists():
            self.delete_cache()
        self._build_cancel = False
        if progress_cb:
            progress_cb({"event": "cache_load_mat", "path": str(self.source_path)})
        loaded = load_amplitude_matrix(self.source_path, self.variable_name)
        self.stats["mat_loads"] += 1
        arr = np.asarray(loaded.data)
        expected_rows = self.frames_per_file * self.height_bins
        if arr.ndim != 2 or arr.shape[1] != self.frequency_bins:
            raise ValueError(f"unexpected_shape:{arr.shape}")
        # Allow smaller synthetic stacks
        n_frames = arr.shape[0] // self.height_bins
        if arr.shape[0] % self.height_bins != 0:
            raise ValueError(f"rows_not_multiple_of_height:{arr.shape}")
        if self._build_cancel:
            return CacheStatus(False, False, str(self.cache_dir), "cancelled")

        import zarr

        ensure_dir(self.cache_dir)
        chunks = (self.height_bins, self.frequency_bins)
        if progress_cb:
            progress_cb({"event": "cache_write_zarr", "shape": list(arr.shape), "chunks": list(chunks)})
        z = zarr.open_array(
            str(self.cache_dir / "data.zarr"),
            mode="w",
            shape=arr.shape,
            chunks=chunks,
            dtype=arr.dtype,
        )
        # write in frame chunks for progress
        for i in range(n_frames):
            if self._build_cancel:
                break
            r0 = i * self.height_bins
            r1 = (i + 1) * self.height_bins
            z[r0:r1, :] = arr[r0:r1, :]
            if progress_cb and (i % 20 == 0 or i == n_frames - 1):
                progress_cb(
                    {
                        "event": "cache_progress",
                        "completed_frames": i + 1,
                        "total_frames": n_frames,
                        "percent": round(100.0 * (i + 1) / n_frames, 1),
                    }
                )
        if self._build_cancel:
            self.delete_cache()
            return CacheStatus(False, False, str(self.cache_dir), "cancelled")

        # validate representative slices
        for idx in (1, max(1, n_frames // 2), n_frames):
            r0 = (idx - 1) * self.height_bins
            r1 = idx * self.height_bins
            if not np.array_equal(z[r0:r1, :], arr[r0:r1, :]):
                raise RuntimeError("cache_validation_failed")

        prov = {
            "identity_key": self.identity.key(),
            "identity": asdict(self.identity),
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "variable_name": self.variable_name,
            "shape": list(arr.shape),
            "n_frames": n_frames,
            "dtype": str(arr.dtype),
            "conversion": "zarr_chunked_copy",
            "cache_format_version": CACHE_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Derived cache only — not new scientific measurements. "
                "Original MAT remains authoritative and unmodified."
            ),
        }
        (self.cache_dir / "provenance.json").write_text(
            json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._open_zarr()
        if progress_cb:
            progress_cb({"event": "cache_ready", "path": str(self.cache_dir)})
        return self.status()

    def cancel_build(self) -> None:
        self._build_cancel = True

    def delete_cache(self) -> None:
        import shutil

        self._zarr = None
        self.lru.clear()
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    def _open_zarr(self) -> None:
        import zarr

        st = self.status()
        if not st.valid:
            raise RuntimeError(f"cache_invalid:{st.reason}")
        self._zarr = zarr.open_array(str(self.cache_dir / "data.zarr"), mode="r")

    def ensure_ready(self, progress_cb: Callable[[dict[str, Any]], None] | None = None) -> CacheStatus:
        st = self.status()
        if st.valid:
            if self._zarr is None:
                self._open_zarr()
            return st
        return self.build_cache(progress_cb=progress_cb)

    def n_frames(self) -> int:
        if self._zarr is not None:
            return int(self._zarr.shape[0] // self.height_bins)
        st = self.status()
        if st.valid and st.provenance:
            return int(st.provenance.get("n_frames", self.frames_per_file))
        return self.frames_per_file

    def get_frame(self, matlab_frame_id: int, prefetch: bool = True) -> np.ndarray:
        cached = self.lru.get(matlab_frame_id)
        if cached is not None:
            self.stats["cache_hits"] += 1
            if prefetch:
                self.prefetch_neighbors(matlab_frame_id)
            return cached
        self.stats["cache_misses"] += 1
        if self._zarr is None:
            self.ensure_ready()
        n = self.n_frames()
        if not (1 <= matlab_frame_id <= n):
            raise IndexError(f"frame_index_out_of_range:{matlab_frame_id}")
        r0 = (matlab_frame_id - 1) * self.height_bins
        r1 = matlab_frame_id * self.height_bins
        with self._lock:
            frame = np.array(self._zarr[r0:r1, :], copy=True)
        self.lru.put(matlab_frame_id, frame)
        if prefetch:
            self.prefetch_neighbors(matlab_frame_id)
        return frame

    def prefetch_neighbors(self, center: int) -> None:
        n = self.n_frames()
        for d in range(1, self.prefetch_radius + 1):
            for fid in (center - d, center + d):
                if 1 <= fid <= n and self.lru.get(fid) is None:
                    try:
                        # avoid recursive prefetch
                        if self._zarr is None:
                            continue
                        r0 = (fid - 1) * self.height_bins
                        r1 = fid * self.height_bins
                        with self._lock:
                            frame = np.array(self._zarr[r0:r1, :], copy=True)
                        self.lru.put(fid, frame)
                    except Exception:  # noqa: BLE001
                        pass
